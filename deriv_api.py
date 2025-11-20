# ------------------------------------
# DERIV API WEBSOCKET — CRYPTOSNIPER FX
# ------------------------------------

import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"  # App ID público

class DerivAPI:

    def __init__(self, token):
        self.token = token
        self.connected = False
        self.ws = None
        self._connect()

    # ------------------------------------
    # CONECTAR AL WEBSOCKET
    # ------------------------------------
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
        print("[DerivAPI] ✔ Conectado. Enviando autorización...")
        self.connected = True
        self.send({"authorize": self.token})

    def _on_message(self, ws, msg):
        data = json.loads(msg)

        if "authorize" in data:
            print("[DerivAPI] 🔐 Token autorizado correctamente.")

        if "error" in data:
            print("[DerivAPI] ❌ Error:", data["error"]["message"])

        if "buy" in data:
            print("[DerivAPI] 🟢 Respuesta de compra:", data)

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Conexión cerrada, intentando reconectar...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error en WebSocket:", error)

    # ------------------------------------
    # ENVIAR AL WS
    # ------------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ WS no conectado, no se pudo enviar.")
            return
        self.ws.send(json.dumps(data))

    # ------------------------------------
    # COMPRAR CONTRATO BINARIO
    # ------------------------------------
    def buy(self, symbol, direction, amount, duration=5):
        """
        Compra contrato CALL/PUT en Deriv.
        """
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

        print(f"[DerivAPI] 🚀 Enviando orden -> {contract} | {symbol} | ${amount} | {duration}m")
        self.send(payload)
