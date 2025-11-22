# ------------------------------------
# DERIV API WEBSOCKET — RESULTADOS WIN/LOSS
# ------------------------------------

import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"

class DerivAPI:

    def __init__(self, token, on_result=None):
        self.token = token
        self.connected = False
        self.ws = None
        self.on_result = on_result  # <- Callback para resultados
        self._connect()

    # ------------------------------------
    # CONECTAR
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
        print("[DerivAPI] 🌍 Conectado. Autorizando...")
        self.connected = True
        self.send({"authorize": self.token})

    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Autoriza
        if "authorize" in data:
            print("[DerivAPI] 🔐 Token autorizado correctamente.")

        # Respuesta de compra
        if data.get("buy"):
            contract_id = data["buy"]["contract_id"]
            print(f"[DerivAPI] 🟢 Contrato abierto: {contract_id}")

            # Pedir actualización del contrato
            self.send({"proposal_open_contract": 1, "contract_id": contract_id})

        # Respuesta de un contrato abierto
        if data.get("proposal_open_contract"):
            poc = data["proposal_open_contract"]

            if poc.get("is_sold"):
                pnl = poc["profit"]
                result = "WIN" if pnl > 0 else "LOSS"
                print(f"[DerivAPI] 🎯 Contrato cerrado: {result} | Profit: {pnl}")

                # Llamar callback para guardar estadística
                if self.on_result:
                    self.on_result(result, pnl)

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Desconectado. Reintentando...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error WebSocket:", error)

    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ No conectado, no se envió.")
            return
        self.ws.send(json.dumps(data))

    # ------------------------------------
    # COMPRAR CONTRATO
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

        print(f"[DerivAPI] 🚀 Orden -> {contract} {symbol} ${amount}")
        self.send(payload)
