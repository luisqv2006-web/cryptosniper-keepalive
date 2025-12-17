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
        
        # Reportar errores de la API directamente
        if 'error' in data:
            error_msg = data['error'].get('message', 'Error desconocido')
            print(f"DERIV ERROR: {error_msg}")
            # Esto permitirá que main.py capture el error real
            self.last_error = error_msg
            return

        if 'msg_type' in data:
            if data['msg_type'] == 'authorize':
                self.is_authenticated = True
                print("Autenticación Exitosa")
            
            elif data['msg_type'] == 'buy':
                print("Orden enviada exitosamente al servidor.")
                self.subscribe_to_transaction(data['buy']['contract_id'])

            elif data['msg_type'] == 'proposal_open_contract':
                contract = data['proposal_open_contract']
                if contract.get('is_expired') == 1:
                    result = "WIN" if contract['profit'] > 0 else "LOSS"
                    self.on_trade_result(result)

    def _on_error(self, ws, error):
        print(f"WS Error: {error}")

    def _on_close(self, ws, status, msg):
        self.is_authenticated = False

    def authenticate(self):
        self.ws.send(json.dumps({"authorize": self.token}))

    def buy(self, symbol, direction, amount, duration):
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
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        self.ws.send(json.dumps(payload))

    def subscribe_to_transaction(self, contract_id):
        self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
