# ------------------------------------
# DERIV API WEBSOCKET — CRYPTOSNIPER FX
# ------------------------------------

import websocket
import json
import threading
import time

# Usa el endpoint correcto para Deriv (NO binaryws)
WS_ENDPOINT = "wss://ws.derivws.com/websockets/v3"
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
        print("[DerivAPI] 🌐 Conectando al WebSocket...")
        self.ws = websocket.WebSocketApp(
            f"{WS_ENDPOINT}?app_id={DERIV_APP_ID}",
            on_open=self._on_open,
            on_message=self._on_message,
            on_close=self._on_close,
            on_error=self._on_error
        )

        # Hilo para mantener conexión activa
        threading.Thread(target=self.ws.run_forever).start()
        time.sleep(1)

    def _on_open(self, ws):
        print("[DerivAPI] ✔ Conectado. Enviando autorización...")
        self.connected = True
        self.send({"authorize": self.token})

    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Respuesta de autorización
        if "authorize" in data:
            if "error" in data["authorize"]:
                print("[DerivAPI] ❌ Error al autorizar token:", data["authorize"]["error"]["message"])
            else:
                print("[DerivAPI] 🔐 Token autorizado correctamente.")

        # Errores generales
        if "error" in data:
            print("[DerivAPI] ❌ ERROR API:", data["error"]["message"])

        # Confirmación de compra
        if "buy" in data:
            print("[DerivAPI] 🟢 Respuesta de compra:", data)

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Conexión cerrada. Reintentando en 1s...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error en WebSocket:", error)

    # ------------------------------------
    # ENVIAR AL WEBSOCKET
    # ------------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ WS no conectado, no se pudo enviar.")
            return
        self.ws.send(json.dumps(data))

    # ------------------------------------
    # REALIZAR COMPRA BINARIA
    # ------------------------------------
    def buy(self, symbol, direction, amount, duration=5):
        """
        Compra contrato CALL o PUT en Deriv
        direction: BUY -> CALL | SELL -> PUT
        """

        contract = "CALL" if direction.upper() == "BUY" else "PUT"

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

        print(f"[DerivAPI] 🚀 Orden enviada -> {contract} | {symbol} | ${amount} | {duration}m")
        self.send(payload)
