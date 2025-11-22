# ------------------------------------
# DERIV API WEBSOCKET — AUTO RESULTADOS
# ------------------------------------

import websocket
import json
import threading
import time

DERIV_APP_ID = "1089"

class DerivAPI:

    def __init__(self, token, on_result_callback=None):
        """
        on_result_callback = función que recibe el profit cuando una operación termina
        Ej:
           def resultado(profit):
               print("Profit:", profit)
        """
        self.token = token
        self.connected = False
        self.ws = None

        # callback para RiskManager
        self.on_result_callback = on_result_callback

        # inicia conexión
        self._connect()

        # heartbeat
        threading.Thread(target=self.heartbeat, daemon=True).start()

    # ------------------------------------
    # CONEXIÓN WEBSOCKET
    # ------------------------------------
    def _connect(self):
        self.ws = websocket.WebSocketApp(
            f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}",
            on_open=self._on_open,
            on_message=self._on_message,
            on_close=self._on_close,
            on_error=self._on_error
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        time.sleep(1)

    def _on_open(self, ws):
        self.connected = True
        print("[DerivAPI] ✔ Conectado.")
        self.send({"authorize": self.token})

        # suscribir a contratos activos
        self.send({"subscribe": 1, "proposal_open_contract": 1})

    # ------------------------------------
    # RECEPCIÓN DE MENSAJES
    # ------------------------------------
    def _on_message(self, ws, msg):
        data = json.loads(msg)

        # Autorización
        if "authorize" in data:
            print("[DerivAPI] 🔐 Token autorizado correctamente.")

        # Error
        if "error" in data:
            print("[DerivAPI] ❌ Error:", data["error"]["message"])
            return

        # Confirmación de compra
        if "buy" in data:
            print("[DerivAPI] 🟢 Compra enviada:", data)

        # Contrato finalizado (resultado real)
        if "proposal_open_contract" in data:
            contract = data["proposal_open_contract"]

            if contract.get("is_sold"):  # el contrato ya terminó
                profit = contract.get("profit", 0)
                
                print(f"[DerivAPI] 📉 Contrato finalizado | Profit: {profit}")

                # mandar resultado al RiskManager si existe callback
                if self.on_result_callback:
                    self.on_result_callback(profit)

    def _on_close(self, ws):
        print("[DerivAPI] ⚠ Conexión cerrada. Reintentando...")
        self.connected = False
        time.sleep(3)
        self._connect()

    def _on_error(self, ws, error):
        print("[DerivAPI] ❌ Error en WebSocket:", error)
        self.connected = False

    # ------------------------------------
    # HEARTBEAT
    # ------------------------------------
    def heartbeat(self):
        while True:
            if not self.connected:
                print("[DerivAPI] 🔁 Intentando reconexión por heartbeat...")
                self._connect()
            time.sleep(60)

    # ------------------------------------
    # ENVIAR
    # ------------------------------------
    def send(self, data):
        if not self.connected:
            print("[DerivAPI] ❌ WS no conectado, no se pudo enviar.")
            return
        self.ws.send(json.dumps(data))

    # ------------------------------------
    # COMPRAR
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

        print(f"[DerivAPI] 🚀 Orden -> {contract} | {symbol} | ${amount}")
        self.send(payload)
