# ------------------------------------
# DERIV API WEBSOCKET — AUTO RESULTADOS WIN/LOSS
# ------------------------------------

import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"  # App ID público para conexión WebSocket

class DerivAPI:

    def __init__(self, token, on_result=None):
        """
        token = Token de Deriv
        on_result = Función callback que recibe (result, profit)
        """
        self.token = token
        self.connected = False
        self.ws = None
        self.on_result = on_result
        self._connect()

    # ------------------------------------
    # CONECTAR WEBSOCKET
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
        print("[DerivAPI] 🌐 Conectado. Autorizando...")
        self.connected = True
        self.send({"authorize": self.token})

    # ------------------------------------
    # RECIBIR MENSAJES
    # ------------------------------------
    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Autorización exitosa
        if "authorize" in data:
            print("[DerivAPI] 🔐 Token autorizado correctamente.")

        # Respuesta de compra
        if data.get("buy"):
            contract_id = data["buy"]["contract_id"]
            print(f"[DerivAPI] 🟢 Contrato abierto: {contract_id}")

            # Solicitar seguimiento del contrato
            self.send({
                "proposal_open_contract": 1,
                "contract_id": contract_id
            })

        # Respuesta de contrato en ejecución o cerrado
        if data.get("proposal_open_contract"):

            poc = data["proposal_open_contract"]

            # Si todavía no se cierra, ignorar
            if not poc.get("is_sold"):
                return
            
            pnl = poc["profit"]
            result = "WIN" if pnl > 0 else "LOSS"

            print(f"[DerivAPI] 🎯 Contrato cerrado: {result} | {pnl:.2f} USD")

            # Ejecutar callback (registra resultado en el bot)
            if self.on_result:
                try:
                    self.on_result(result, pnl)
                except Exception as e:
                    print("[DerivAPI] ❌ Error en callback:", e)

    # ------------------------------------
    # ERRORES / RECONEXIÓN
    # ------------------------------------
    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Desconectado, reconectando...")
        self.connected = False
        time.sleep(1)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error WebSocket:", error)

    # ------------------------------------
    # ENVIAR MENSAJES WS
    # ------------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ No conectado, no se pudo enviar.")
            return
        self.ws.send(json.dumps(data))

    # ------------------------------------
    # ENVIAR ORDEN (COMPRA BINARIA)
    # ------------------------------------
    def buy(self, symbol, direction, amount, duration=5):
        """
        Ejecuta una operación real en Deriv
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

        print(f"[DerivAPI] 🚀 Orden enviada -> {contract} {symbol} | ${amount}")
        self.send(payload)
