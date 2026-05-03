import websocket
import json
import time
import threading

class DerivAPI:
    def __init__(self, token, on_trade_result_callback, endpoint="wss://ws.derivws.com/websockets/v3?app_id=1089"):
        self.token = token
        self.on_trade_result = on_trade_result_callback  # ahora espera (contract_id, result)
        self.url = endpoint
        self.ws = None
        self.is_authenticated = False
        self.processed_contracts = set()
        self.buy_event = threading.Event()
        self.candles_event = threading.Event()
        self.balance_event = threading.Event()   # Nuevo
        self.last_buy_response = None
        self.last_candles_data = None
        self.last_balance_data = None            # Nuevo
        self.last_error = None
        self.connect()

    def connect(self):
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            threading.Thread(target=self.ws.run_forever, daemon=True).start()
            time.sleep(2)
        except Exception as e:
            raise ConnectionError(f"Fallo inicial de WebSocket: {e}")

    def _on_open(self, ws):
        print("Conectado. Autenticando...")
        self.authenticate()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
        except:
            return
        if 'error' in data:
            self.last_error = data['error']['message']
            self.buy_event.set()
            self.candles_event.set()
            self.balance_event.set()
            return
        if 'msg_type' in data:
            if data['msg_type'] == 'authorize':
                self.is_authenticated = True
                print("Autenticado correctamente.")
            elif data['msg_type'] == 'buy':
                if 'buy' in data:
                    self.last_buy_response = data['buy']
                    self.last_error = None
                    self.buy_event.set()
                    self.subscribe_to_transaction(data['buy']['contract_id'])
            elif data['msg_type'] == 'candles':
                self.last_candles_data = data['candles']
                self.candles_event.set()
            elif data['msg_type'] == 'get_self':
                # Respuesta a get_self, contiene balance
                balance = data.get("get_self", {}).get("balance")
                if balance:
                    self.last_balance_data = float(balance)
                else:
                    self.last_balance_data = None
                self.balance_event.set()
            elif data['msg_type'] == 'proposal_open_contract':
                contract = data['proposal_open_contract']
                contract_id = contract['contract_id']
                if contract_id in self.processed_contracts:
                    return
                if contract.get('is_expired') == 1 and contract.get('status') != 'open':
                    profit = contract.get('profit', 0)
                    result = "WIN" if profit > 0 else "LOSS"
                    self.processed_contracts.add(contract_id)
                    # Llamar al callback con contract_id y resultado
                    self.on_trade_result(contract_id, result)

    def _on_error(self, ws, error):
        self.last_error = str(error)
        self.buy_event.set()
        self.candles_event.set()
        self.balance_event.set()

    def _on_close(self, ws, status, msg):
        self.is_authenticated = False
        print("Conexión cerrada.")

    def authenticate(self):
        self.ws.send(json.dumps({"authorize": self.token}))

    def _ensure_connected(self):
        if not self.ws or not self.ws.sock:
            self.connect()
            time.sleep(2)

    def get_candles(self, symbol, interval_minutes, count=60):
        self._ensure_connected()
        self.candles_event.clear()
        self.last_candles_data = None
        granularity = int(interval_minutes * 60)
        payload = {
            "ticks_history": symbol,
            "adjust_start_time": 1,
            "count": count,
            "end": "latest",
            "style": "candles",
            "granularity": granularity
        }
        try:
            self.ws.send(json.dumps(payload))
            if self.candles_event.wait(timeout=5):
                return self.last_candles_data
            return None
        except Exception as e:
            print(f"Error pidiendo velas: {e}")
            return None

    def buy(self, symbol, direction, amount, duration, duration_unit="m"):
        max_retries = 2
        for attempt in range(max_retries):
            self._ensure_connected()
            if not self.is_authenticated:
                self.authenticate()
                start = time.time()
                while not self.is_authenticated and (time.time() - start) < 5:
                    time.sleep(0.2)
                if not self.is_authenticated:
                    raise Exception("No se pudo autenticar")

            self.buy_event.clear()
            self.last_buy_response = None
            self.last_error = None

            side = "CALL" if direction.upper() == "BUY" else "PUT"
            payload = {
                "buy": 1,
                "price": amount,
                "parameters": {
                    "amount": amount,
                    "basis": "stake",
                    "contract_type": side,
                    "currency": "USD",
                    "duration": duration,
                    "duration_unit": duration_unit,
                    "symbol": symbol
                }
            }
            self.ws.send(json.dumps(payload))
            received = self.buy_event.wait(timeout=10)
            if not received:
                raise TimeoutError("Deriv no respondió en 10s.")
            if self.last_error and "log in" in self.last_error:
                print("Sesión perdida. Reautenticando...")
                self.is_authenticated = False
                continue
            break
        if self.last_error:
            raise Exception(f"RECHAZADO: {self.last_error}")
        if self.last_buy_response:
            return self.last_buy_response['contract_id']
        raise Exception("Error desconocido.")

    def get_balance(self):
        """Obtiene el saldo real de la cuenta. Devuelve float o None."""
        self._ensure_connected()
        if not self.is_authenticated:
            self.authenticate()
            start = time.time()
            while not self.is_authenticated and (time.time() - start) < 5:
                time.sleep(0.2)
            if not self.is_authenticated:
                return None
        self.balance_event.clear()
        self.last_balance_data = None
        self.ws.send(json.dumps({"get_self": 1}))
        if self.balance_event.wait(timeout=5):
            return self.last_balance_data
        return None

    def subscribe_to_transaction(self, contract_id):
        self.ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
