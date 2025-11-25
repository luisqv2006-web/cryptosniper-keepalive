# ============================================================
# DERIV API — CryptoSniper FX
# WebSocket PRO + Reconexión + Callback de Resultados
# ============================================================

import json
import websocket
import threading
import time

DERIV_APP_ID = "1089"  # app_id público válido

class DerivAPI:

    def __init__(self, token, on_result_callback=None):
        self.token = token
        self.on_result_callback = on_result_callback
        self.ws = None
        self.connected = False

        self._connect()

    # ==================================================================
    # 🔌 CONEXIÓN AL WEBSOCKET
    # ==================================================================
    def _connect(self):
        try:
            self.ws = websocket.WebSocketApp(
                f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}",
                on_open=self._on_open,
                on_message=self._on_message,
                on_close=self._on_close,
                on_error=self._on_error
            )

            t = threading.Thread(target=self.ws.run_forever)
            t.daemon = True
            t.start()

            time.sleep(1)

        except Exception:
            self.connected = False
            time.sleep(2)
            self._connect()

    # ==================================================================
    # 🔓 AUTORIZACIÓN
    # ==================================================================
    def _on_open(self, ws):
        self.connected = True
        self.send({"authorize": self.token})

    # ==================================================================
    # 📥 RESPUESTAS DEL WEBSOCKET
    # ==================================================================
    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Confirmación de autorización
        if "authorize" in data:
            return

        # Resultado real del contrato
        if "proposal_open_contract" in data:
            try:
                profit = data["proposal_open_contract"]["profit"]
                if self.on_result_callback:
                    self.on_result_callback(float(profit))
            except:
                pass

        # Respuesta de compra
        if "buy" in data:
            return

    # ==================================================================
    # 🔌 MANEJO DE ERRORES Y RECONEXIONES
    # ==================================================================
    def _on_close(self, ws):
        self.connected = False
        time.sleep(2)
        self._connect()

    def _on_error(self, ws, error):
        self.connected = False
        time.sleep(2)
        self._connect()

    # ==================================================================
    # 📤 ENVIAR MENSAJE AL WS
    # ==================================================================
    def send(self, data):
        if not self.connected:
            time.sleep(1)
            return
        try:
            self.ws.send(json.dumps(data))
        except:
            self.connected = False
            self._connect()

    # ==================================================================
    # 🟢 EJECUTAR COMPRA REAL
    # ==================================================================
    def buy(self, symbol, direction, amount, duration=5):
        contract = "CALL" if direction == "BUY" else "PUT"

        payload = {
            "buy": "1",
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contract,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m",
                "symbol": symbol
            }
        }

        self.send(payload)
