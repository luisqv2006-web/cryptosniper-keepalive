# =============================================================
# DERIV API — Conexión Única Optimizada (Render FREE)
# =============================================================

import websocket
import threading
import json
import time

DERIV_APP_ID = "1089"

class DerivAPI:
    def __init__(self, token, on_result_callback=None):
        self.token = token
        self.on_result = on_result_callback
        self.ws = None
        self.connected = False
        self._start_ws()

    # ============================
    # Inicia WebSocket
    # ============================
    def _start_ws(self):
        def run():
            self.ws = websocket.WebSocketApp(
                f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}",
                on_open=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error,
                on_message=self._on_message
            )
            self.ws.run_forever()

        threading.Thread(target=run, daemon=True).start()
        time.sleep(1)

    def _on_open(self, ws):
        self.connected = True
        self.send({"authorize": self.token})

    def _on_close(self, ws):
        self.connected = False
        time.sleep(2)
        self._start_ws()  # reconexión suave

    def _on_error(self, ws, error):
        self.connected = False

    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Resultado de contrato finalizado
        if "profit" in str(data):
            try:
                profit = float(data["profit"])
                if self.on_result:
                    self.on_result(profit)
            except:
                pass

    # ============================
    # Enviar mensaje WS
    # ============================
    def send(self, data):
        if self.connected:
            try:
                self.ws.send(json.dumps(data))
            except:
                pass

    # ============================
    # Comprar contrato
    # ============================
    def buy(self, symbol, direction, amount, duration):
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
                "duration_unit": "m"
            }
        }
        self.send(payload)
