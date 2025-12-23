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
        
        # Eventos
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
        
        if 'error' in data:
            self.last_error = data['error']['message']
            self.buy_event.set()
            return

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

    def buy(self, symbol, direction, amount, duration, duration_unit="m"):
        # REINTENTO AUTOMÁTICO DE LOGIN
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
            
            # Esperar respuesta
            received = self.buy_event.wait(timeout=10)
            
            if not received:
                raise TimeoutError("Deriv no respondió en 10s.")
            
            # Si el error es 'Please log in', re-autenticamos y reintentamos el loop
            if self.last_error and "log in" in self.last_error:
                print("Sesión perdida. Re-autenticando y reintentando...")
                self.is_authenticated = False
                self.authenticate()
                time.sleep(2)
                continue # Vuelve al inicio del for para reintentar la compra
            
            # Si es otro error o éxito, salimos del loop
            break

        if self.last_error:
            raise Exception(f"RECHAZADO: {self.last_error}")
            
        if self.last_buy_response:
            return self.last_buy_response['contract_id']
            
        raise Exception("Error desconocido.")

    def subscribe_to_transaction(self, contract_id):
        self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
