import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"

class DerivAPI:

    def __init__(self, token):
        self.token = token
        self.connected = False
        self.ws = None
        self._connect()

    def _connect(self):
        self.ws = websocket.WebSocketApp(
            f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}",
            on_open=self._on_open,
            on_message=self._on_message,
            on_close=self._on_close,
            on_error=self._on_error
        )
        threading.Thread(target=self.ws.run_forever).start()
        time.sleep(1)

    def _on_open(self, ws):
        self.connected = True
        self.send({"authorize": self.token})

    def _on_message(self, ws, msg):
        data = json.loads(msg)
        if "error" in data:
            print("Deriv Error:", data["error"]["message"])

    def _on_close(self, ws):
        self.connected = False
        print("Conexión cerrada. Reintentando...")
        time.sleep(2)
        self._connect()

    def _on_error(self, ws, error):
        print("WebSocket Error:", error)

    def send(self, data):
        if self.connected:
            self.ws.send(json.dumps(data))

    def buy(self, symbol, direction, amount=1, duration=5):
        contract = "CALL" if direction == "BUY" else "PUT"

        payload = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contract,
                "symbol": symbol,
                "duration": duration,
                "duration_unit": "m",
                "currency": "USD"
            }
        }

        self.send(payload)
