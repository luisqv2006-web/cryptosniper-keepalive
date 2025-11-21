# ------------------------------------
# DERIV API WEBSOCKET — CRYPTOSNIPER FX (Versión Optimizada)
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

        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True   # <-- Esto evita que Render mate el socket
        t.start()

        # Esperar conexión antes de autorizar
        for _ in range(10):
            if self.connected:
                break
            time.sleep(0.5)

    # ------------------------------------
    # EVENTOS DEL WS
    # ------------------------------------
    def _on_open(self, ws):
        print("[DerivAPI] ✔ Conectado con Deriv. Autorizando token...")
        self.send({"authorize": self.token})

    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Autorización
        if data.get("authorize"):
            print("[DerivAPI] 🔐 Token autorizado correctamente.")
            self.connected = True

        # Errores
        if "error" in data:
            print("❌ [DerivAPI ERROR]:", data["error"]["message"])

        # Confirmación de compra
        if "buy" in data:
            contract_id = data["buy"].get("contract_id")
            print(f"🟢 Operación ejecutada con éxito | Contract ID: {contract_id}")

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ WebSocket cerrado. Reintentando...")
        self.connected = False
        time.sleep(2)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error en WebSocket:", error)

    # ------------------------------------
    # ENVIAR DATOS
    # ------------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ No conectado. Reintentando...")
            self._connect()
            time.sleep(1)

        try:
            self.ws.send(json.dumps(data))
        except Exception as e:
            print("❌ Error al enviar datos:", e)

    # ------------------------------------
    # COMPRAR CONTRATO BINARIO
    # ------------------------------------
    def buy(self, symbol, direction, amount, duration=5):
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
