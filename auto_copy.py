# =============================================================
#  AUTO COPY TRADER — CryptoSniper v8.3
# =============================================================

import json
from websocket import create_connection

class AutoCopy:

    def __init__(self, token, stake=1, duration=5):
        self.token = token
        self.amount = stake
        self.duration = duration

    def open(self, direction, symbol):
        try:
            ws = create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089")

            ws.send(json.dumps({"authorize": self.token}))
            ws.recv()

            contract_type = "CALL" if direction == "BUY" else "PUT"

            ws.send(json.dumps({
                "buy": 1,
                "price": self.amount,
                "parameters": {
                    "amount": self.amount,
                    "basis": "stake",
                    "contract_type": contract_type,
                    "currency": "USD",
                    "duration": self.duration,
                    "duration_unit": "m",
                    "symbol": symbol
                }
            }))

            print(f"[AutoCopy] 🌀 Copiando orden: {direction} {symbol}")

        except Exception as e:
            print("[AutoCopy] Error:", e)
