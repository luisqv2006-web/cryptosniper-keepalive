# ------------------------------------
# DERIV API WEBSOCKET — CRYPTOSNIPER FX (CON RESULTADOS)
# ------------------------------------

import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"

class DerivAPI:

    def __init__(self, token):
        self.token = token
        self.connected = False
        self.ws = None
        self.active_contracts = {}   # 📌 Guardamos contract_id -> direction
        self.on_result = None        # 📌 Callback para notificar al bot
        self._connect()

    # ------------------------------------
    # CONEXIÓN
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
        print("[DerivAPI] ✔ Conectado. Autorizando...")
        self.connected = True
        self.send({"authorize": self.token})

    # ------------------------------------
    # RECEPCIÓN DE MENSAJES
    # ------------------------------------
    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Confirmación de token
        if "authorize" in data:
            print("[DerivAPI] 🔑 Token autorizado correctamente")

        # Captura errores
        if "error" in data:
            print("[DerivAPI] ❌ Error:", data["error"]["message"])
            return
        
        # 📌 Cuando se ejecuta una compra
        if "buy" in data and "contract_id" in data["buy"]:
            cid = data["buy"]["contract_id"]
            self.active_contracts[cid] = True
            print("[DerivAPI] 📌 Contrato creado:", cid)

            # Nos suscribimos al resultado de ese contrato
            self.send({
                "proposal_open_contract": 1,
                "contract_id": cid,
                "subscribe": 1
            })

        # 📌 Cuando el contrato finaliza
        if "proposal_open_contract" in data:
            poc = data["proposal_open_contract"]

            if poc.get("is_sold"):
                cid = poc.get("contract_id")
                profit = poc.get("profit")
                result = "WIN" if profit > 0 else "LOSS"

                print(f"[DerivAPI] 🎯 Contrato finalizado: {cid} → {result} | Ganancia: {profit}")

                if self.on_result:
                    self.on_result({
                        "contract_id": cid,
                        "profit": profit,
                        "result": result
                    })

                del self.active_contracts[cid]

    # ------------------------------------
    # EVENTOS WS
    # ------------------------------------
    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Conexión cerrada. Reintentando...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ⚠ Error:", error)

    # ------------------------------------
    # ENVIAR
    # ------------------------------------
    def send(self, data):
        if self.connected:
            self.ws.send(json.dumps(data))
        else:
            print("[DerivAPI] ❌ No hay conexión activa")

    # ------------------------------------
    # ENVIAR ORDEN
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

        print(f"[DerivAPI] 🚀 Orden enviada -> {symbol} | {direction} | ${amount}")
        self.send(payload)
