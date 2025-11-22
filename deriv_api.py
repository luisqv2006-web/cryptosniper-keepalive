import websocket
import json
import time

class DerivAPI:
    def __init__(self, token):
        self.token = token
        self.ws = None
        self.account_id = None

        self.connect()
        self.authorize()

    def connect(self):
        print("[DerivAPI] 🌐 Conectando al WebSocket...")
        self.ws = websocket.create_connection("wss://ws.deriv.com/websockets/v3?app_id=16929")

    def send(self, data):
        self.ws.send(json.dumps(data))
        return json.loads(self.ws.recv())

    def authorize(self):
        res = self.send({"authorize": self.token})
        
        if "error" in res:
            print("[DerivAPI] ❌ Error autorización ->", res)
            return
        
        print("[DerivAPI] 🔐 Token autorizado correctamente.")

        # Obtener lista de cuentas
        resp = self.send({"get_account_status": 1})
        
        # Obtener login ID de la cuenta predeterminada
        login_data = self.send({"account_list": 1})
        try:
            self.account_id = login_data["account_list"][0]["loginid"]
            print(f"[DerivAPI] 🧾 Usando cuenta: {self.account_id}")
        except:
            print("[DerivAPI] ⚠ No se pudo obtener account_id")

    def buy(self, symbol, direction, amount, duration=5):
        if not self.account_id:
            print("[DerivAPI] ❌ No hay cuenta activa, no se puede operar.")
            return

        contract = {
            "buy": 1,
            "price": amount,
            "subscribe": 1,
            "parameters": {
                "contract_type": "CALL" if direction == "BUY" else "PUT",
                "symbol": symbol,
                "duration": duration,
                "duration_unit": "m",
                "basis": "stake",
                "currency": "USD"
            },
            "account_id": self.account_id
        }

        print("[DerivAPI] 🚀 Enviando orden...", contract)

        res = self.send(contract)

        if "error" in res:
            print("[DerivAPI] ❌ Error al ejecutar:", res["error"])
        else:
            print("[DerivAPI] ✔ Orden ejecutada correctamente.")
            print(res)
