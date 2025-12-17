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
        
        # Variables para controlar la respuesta del servidor
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
            time.sleep(3) 
        except Exception as e:
            raise ConnectionError(f"Fallo inicial de WebSocket: {e}")

    def _on_open(self, ws):
        self.authenticate()

    def _on_message(self, ws, message):
        data = json.loads(message)
        
        # 1. Si hay un error explícito del servidor
        if 'error' in data:
            self.last_error = data['error']['message']
            # Si estábamos esperando una compra, desbloqueamos el proceso
            self.buy_event.set() 
            print(f"DERIV ERROR: {self.last_error}")
            return

        # 2. Procesar mensajes normales
        if 'msg_type' in data:
            if data['msg_type'] == 'authorize':
                self.is_authenticated = True
                print("Autenticación Exitosa")
            
            elif data['msg_type'] == 'buy':
                # ¡RESPUESTA DE COMPRA RECIBIDA!
                if 'buy' in data:
                    self.last_buy_response = data['buy']
                    self.last_error = None # Limpiamos errores anteriores
                    self.buy_event.set() # Desbloqueamos el proceso
                    self.subscribe_to_transaction(data['buy']['contract_id'])

            elif data['msg_type'] == 'proposal_open_contract':
                contract = data['proposal_open_contract']
                if contract.get('is_expired') == 1:
                    result = "WIN" if contract['profit'] > 0 else "LOSS"
                    self.on_trade_result(result)

    def _on_error(self, ws, error):
        print(f"WS Error: {error}")
        self.last_error = str(error)
        self.buy_event.set() # Desbloquear si hay error de red

    def _on_close(self, ws, status, msg):
        self.is_authenticated = False

    def authenticate(self):
        self.ws.send(json.dumps({"authorize": self.token}))

    def buy(self, symbol, direction, amount, duration):
        # 1. Limpiar eventos anteriores
        self.buy_event.clear()
        self.last_buy_response = None
        self.last_error = None

        if not self.is_authenticated:
            self.authenticate()
            time.sleep(1)

        side = "CALL" if direction.upper() == "BUY" else "PUT"
        
        # Payload estándar para Opciones Binarias (Rise/Fall)
        payload = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": side,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        
        # 2. Enviar la orden
        self.ws.send(json.dumps(payload))
        
        # 3. ESPERAR RESPUESTA (Bloqueo Síncrono) - Máximo 10 segundos
        received = self.buy_event.wait(timeout=10)
        
        # 4. Analizar qué pasó
        if not received:
            raise TimeoutError("El servidor de Deriv no respondió en 10 segundos.")
        
        if self.last_error:
            raise Exception(f"RECHAZADO POR DERIV: {self.last_error}")
            
        if self.last_buy_response:
            return self.last_buy_response['contract_id']
            
        raise Exception("Error desconocido al intentar comprar.")

    def subscribe_to_transaction(self, contract_id):
        self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
