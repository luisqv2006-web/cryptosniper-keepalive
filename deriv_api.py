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
        
        # Eventos de sincronización
        self.buy_event = threading.Event()
        self.last_buy_response = None
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
        data = json.loads(message)
        
        # 1. Capturar errores explícitos
        if 'error' in data:
            self.last_error = data['error']['message']
            self.buy_event.set() # Desbloquear el proceso si hay error
            return

        # 2. Procesar mensajes
        if 'msg_type' in data:
            if data['msg_type'] == 'authorize':
                self.is_authenticated = True
                print("Autenticado correctamente.")
            
            elif data['msg_type'] == 'buy':
                if 'buy' in data:
                    self.last_buy_response = data['buy']
                    self.last_error = None
                    self.buy_event.set() # Desbloquear proceso con éxito
                    self.subscribe_to_transaction(data['buy']['contract_id'])

            elif data['msg_type'] == 'proposal_open_contract':
                contract = data['proposal_open_contract']
                if contract.get('is_expired') == 1:
                    result = "WIN" if contract['profit'] > 0 else "LOSS"
                    self.on_trade_result(result)

    def _on_error(self, ws, error):
        self.last_error = str(error)
        self.buy_event.set()

    def _on_close(self, ws, status, msg):
        self.is_authenticated = False
        print("Conexión cerrada.")

    def authenticate(self):
        self.ws.send(json.dumps({"authorize": self.token}))

    # CORRECCIÓN AQUÍ: Se añade duration_unit por defecto para evitar el error
    def buy(self, symbol, direction, amount, duration, duration_unit="m"):
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
                "duration_unit": duration_unit, # Ahora usa el parámetro correcto
                "symbol": symbol
            }
        }
        
        self.ws.send(json.dumps(payload))
        
        # ESPERAR RESPUESTA (Bloqueo de seguridad)
        received = self.buy_event.wait(timeout=10)
        
        if not received:
            raise TimeoutError("Deriv no respondió en 10s.")
        
        if self.last_error:
            raise Exception(f"RECHAZADO: {self.last_error}")
            
        if self.last_buy_response:
            return self.last_buy_response['contract_id']
            
        raise Exception("Error desconocido.")

    def subscribe_to_transaction(self, contract_id):
        self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
