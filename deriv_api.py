# =============================================================
# DERIV API WEBSOCKET — CRYPTOSNIPER FX
# Conexión directa para ejecución de contratos
# =============================================================

import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"

class DerivAPI:

    def __init__(self, token, on_result_callback=None):
        self.token = token
        self.connected = False
        self.ws = None
        self.on_result_callback = on_result_callback
        self._connect()

    # --------------------------------------------
    # CONECTAR
    # --------------------------------------------
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
        print("[DerivAPI] ✔ Conectado. Autorizando...")
        self.connected = True
        self.send({"authorize": self.token})

    # --------------------------------------------
    # EVENTOS
    # --------------------------------------------
    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # TOKEN VALIDADO
        if data.get("authorize"):
            print("[DerivAPI] 🔐 Token autorizado correctamente.")

        # RESPUESTA DE COMPRA
        if data.get("buy"):
            print("[DerivAPI] 🟢 Orden enviada:", data)

        # ERRORES
        if "error" in data:
            print("[DerivAPI] ❌ Error:", data["error"]["message"])

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Conexión cerrada. Reintentando...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error:", error)

    # --------------------------------------------
    # ENVIAR MENSAJES
    # --------------------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ No conectado.")
            return
        self.ws.send(json.dumps(data))

    # --------------------------------------------
    # COMPRAR CONTRATO
    # --------------------------------------------
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

        print(f"[DerivAPI] 🚀 Enviando: {contract} | {symbol} | ${amount} | {duration}m")
        self.send(payload)
