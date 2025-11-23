# ==============================================================
# DERIV API — Seguimiento de contratos + resultados automáticos
# ==============================================================

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
        
        self.contracts_activos = {}  # {contract_id: {"symbol":..., "direction":...}}

        self._connect()

    # -------------------------------
    # 🔌 Conexión WebSocket
    # -------------------------------
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

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Conexión cerrada, reconectando...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error:", error)

    # -------------------------------
    # 📩 Manejo de mensajes entrantes
    # -------------------------------
    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Autorizado
        if "authorize" in data:
            print("[DerivAPI] 🔑 Token autorizado.")

        # Error general
        if "error" in data:
            print("[DerivAPI] ❌ Error:", data["error"]["message"])

        # Respuesta de compra
        if "buy" in data:
            contrato = data.get("buy", {})
            contract_id = contrato.get("contract_id")
            symbol = contrato.get("symbol", "Desconocido")

            if contract_id:
                print(f"[DerivAPI] 🟢 Contrato enviado: {contract_id}")
                
                self.contracts_activos[contract_id] = {
                    "symbol": symbol,
                    "entry_tick": contrato.get("entry_tick", None)
                }

                # 🔍 Suscribirse para monitorear resultado
                self.send({"proposal_open_contract": 1, "contract_id": contract_id})

        # Seguimiento del contrato
        if "proposal_open_contract" in data:
            contrato = data["proposal_open_contract"]
            contract_id = contrato.get("contract_id")

            if contract_id:
                if contrato.get("is_sold"):
                    profit = contrato.get("profit", 0)
                    
                    print(f"[RESULTADO] Contrato {contract_id} cerrado | Profit: {profit}")

                    if self.on_result_callback:
                        self.on_result_callback(profit)

                    # Eliminar de lista activa
                    self.contracts_activos.pop(contract_id, None)


    # -------------------------------
    # 📤 Enviar datos al WebSocket
    # -------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ WebSocket no conectado.")
            return
        self.ws.send(json.dumps(data))


    # -------------------------------
    # 🟣 Comprar contrato CALL/PUT
    # -------------------------------
    def buy(self, symbol, direction, amount, duration=5):
        contrato = "CALL" if direction == "BUY" else "PUT"

        payload = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contrato,
                "symbol": symbol,
                "duration": duration,
                "duration_unit": "m",
                "currency": "USD"
            }
        }

        print(f"[DerivAPI] 🚀 Orden enviada -> {contrato} | {symbol} | ${amount}")
        self.send(payload)
