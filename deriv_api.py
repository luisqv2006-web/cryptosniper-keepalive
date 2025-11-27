import json
import websocket
import threading

class DerivAPI:
    def __init__(self, token, on_result_callback=None):
        self.token = token
        self.ws = None
        self.on_result_callback = on_result_callback
        threading.Thread(target=self.connect, daemon=True).start()

    def connect(self):
        self.ws = websocket.WebSocketApp(
            "wss://ws.binaryws.com/websockets/v3?app_id=1089",
            on_open=self.on_open,
            on_message=self.on_message
        )
        self.ws.run_forever()

    def on_open(self, ws):
        # ✅ AUTORIZACIÓN REAL
        ws.send(json.dumps({
            "authorize": self.token
        }))

    def on_message(self, ws, message):
        data = json.loads(message)

        # ✅ RESULTADO DE TRADE
        if "proposal_open_contract" in data:
            contract = data["proposal_open_contract"]
            if contract.get("is_sold"):
                profit = float(contract.get("profit", 0))
                result = "WIN" if profit > 0 else "LOSS"

                if self.on_result_callback:
                    self.on_result_callback(result)

        elif "buy" in data:
            print("Trade enviado a Deriv ✅")

    def buy(self, symbol, direction, amount, duration):
        proposal = {
            "buy": 1,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": "CALL" if direction == "BUY" else "PUT",
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }
        self.ws.send(json.dumps(proposal))
