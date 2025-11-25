# =============================================================
#  DERIV API — CryptoSniper v8.3
# =============================================================

import json
import threading
from websocket import create_connection

class DerivAPI:

    def __init__(self, token, on_result_callback=None):
        self.token = token
        self.callback = on_result_callback
        self.ws = None

        threading.Thread(target=self.connect).start()

    def connect(self):
        try:
            self.ws = create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089")
            self._authorize()
        except Exception as e:
            print("[DerivAPI] Error conectando:", e)

    def _authorize(self):
        try:
            self.ws.send(json.dumps({
                "authorize": self.token
            }))

            res = json.loads(self.ws.recv())
            if res.get("authorize"):
                print("[DerivAPI] ✔ Token autorizado.")
            else:
                print("[DerivAPI] ❌ Error al autorizar.")
        except:
            pass

    # =============================================================
    #  EJECUTAR ORDEN BINARIA
    # =============================================================
    def buy(self, symbol, direction, amount=1, duration=5):

        contract_type = "CALL" if direction == "BUY" else "PUT"

        msg = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }

        try:
            self.ws.send(json.dumps(msg))
            print(f"[DerivAPI] ▶ Orden enviada {direction} — {symbol}")
        except Exception as e:
            print("[DerivAPI] Error enviando operación:", e)
