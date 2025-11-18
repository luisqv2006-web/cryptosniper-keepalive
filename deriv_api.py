import json
import websocket

class DerivAPI:
    def __init__(self, token):
        self.token = token
        self.ws = None

    def connect(self):
        self.ws = websocket.create_connection("wss://ws.binaryws.com/websockets/v3?app_id=1089")
        self.authorize()

    def authorize(self):
        auth = {"authorize": self.token}
        self.ws.send(json.dumps(auth))
        return json.loads(self.ws.recv())

    def send(self, data):
        self.ws.send(json.dumps(data))
        return json.loads(self.ws.recv())

    def buy(self, symbol, amount, duration=5):
        contract = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": "CALL",
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        return self.send(contract)

    def sell(self, symbol, amount, duration=5):
        contract = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": "PUT",
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        return self.send(contract)
