import websocket
import json
import time
import threading

class DerivAPI:
    def __init__(self, token, on_trade_result_callback, endpoint="wss://ws.derivws.com/websockets/v3?app_id=1089"):
        self.token = token
        self.on_trade_result = on_trade_result_callback
        self.url = endpoint
        self.ws = None
        self.is_authenticated = False
        
        # MEMORIA PARA EVITAR DUPLICADOS
        self.processed_contracts = set()
        
        # Eventos de sincronización
        self.buy_event = threading.Event()
        self.candles_event = threading.Event()  # <--- NUEVO: Evento para velas
        
        # Datos temporales
        self.last_buy_response = None
        self.last_candles_data = None  # <--- NUEVO: Guardar velas
        self.last_error = None
        
        self.connect()

    def connect(self):
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            threading.Thread(target=self.ws.run_forever, daemon=True).start()
            time.sleep(2) 
        except Exception as e:
            raise ConnectionError(f"Fallo inicial de WebSocket: {e}")

    def _on_open(self, ws):
        print("Conectado. Autenticando...")
        self.authenticate()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except:
            return
        
        # 1. Manejo de Errores
        if 'error' in data:
            self.last_error = data['error']['message']
            self.buy_event.set()
            self.candles_event.set() # Liberar espera de velas si hay error
            return

        # 2. Manejo de Mensajes
        if 'msg_type' in data:
            if data['msg_type'] == 'authorize':
                self.is_authenticated = True
                print("Autenticado correctamente.")
            
            elif data['msg_type'] == 'buy':
                if 'buy' in data:
                    self.last_buy_response = data['buy']
                    self.last_error = None
                    self.buy_event.set()
                    self.subscribe_to_transaction(data['buy']['contract_id'])
            
            # --- NUEVO: Recepción de Velas ---
            elif data['msg_type'] == 'candles':
                self.last_candles_data = data['candles']
                self.candles_event.set()
            # ---------------------------------

            elif data['msg_type'] == 'proposal_open_contract':
                contract = data['proposal_open_contract']
                contract_id = contract['contract_id']
                
                # FILTRO DE DUPLICADOS
                if contract_id in self.processed_contracts:
                    return

                if contract.get('is_expired') == 1 and contract.get('status') != 'open':
                    profit = contract.get('profit', 0)
                    result = "WIN" if profit > 0 else "LOSS"
                    self.processed_contracts.add(contract_id)
                    self.on_trade_result(result)

    def _on_error(self, ws, error):
        self.last_error = str(error)
        self.buy_event.set()
        self.candles_event.set()

    def _on_close(self, ws, status, msg):
        self.is_authenticated = False
        print("Conexión cerrada.")

    def authenticate(self):
        self.ws.send(json.dumps({"authorize": self.token}))

    # --- NUEVA FUNCIÓN: Obtener Velas ---
    def get_candles(self, symbol, interval_minutes, count=60):
        self.candles_event.clear()
        self.last_candles_data = None
        
        # Deriv usa segundos (60, 300, 900...)
        granularity = int(interval_minutes * 60)
        
        payload = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "candles",
            "granularity": granularity
        }
        
        try:
            self.ws.send(json.dumps(payload))
            # Esperamos máximo 5 segundos por los datos
            if self.candles_event.wait(timeout=5):
                return self.last_candles_data
            return None
        except Exception as e:
            print(f"Error pidiendo velas: {e}")
            return None
    # ------------------------------------

    def buy(self, symbol, direction, amount, duration, duration_unit="m"):
        max_retries = 2
        for attempt in range(max_retries):
            self.buy_event.clear()
            self.last_buy_response = None
            self.last_error = None

            if not self.is_authenticated:
                self.authenticate()
                time.sleep(1)

            side = "CALL" if direction.upper() == "BUY" else "PUT"
            
            payload = {
                "buy": 1,
                "price": amount,
                "parameters": {
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": side,
                    "currency": "USD",
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "symbol": symbol
                }
            }
            
            self.ws.send(json.dumps(payload))
            
            received = self.buy_event.wait(timeout=10)
            
            if not received:
                raise TimeoutError("Deriv no respondió en 10s.")
            
            if self.last_error and "log in" in self.last_error:
                print("Sesión perdida. Re-autenticando...")
                self.is_authenticated = False
                self.authenticate()
                time.sleep(2)
                continue
            
            break

        if self.last_error:
            raise Exception(f"RECHAZADO: {self.last_error}")
            
        if self.last_buy_response:
            return self.last_buy_response['contract_id']
            
        raise Exception("Error desconocido.")

    def subscribe_to_transaction(self, contract_id):
        self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
