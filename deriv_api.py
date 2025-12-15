import websocket
import json
import time
import threading
import os

class DerivAPI:
    def __init__(self, token, on_trade_result_callback, endpoint="wss://ws.derivws.com/websockets/v3?app_id=1089"):
        """
        Inicializa la conexión con Deriv.
        Se usa el endpoint 'ws.derivws.com' para mayor estabilidad.
        """
        self.token = token
        self.on_trade_result = on_trade_result_callback
        self.url = endpoint
        self.ws = None
        self.connect()

    def connect(self):
        """Intenta establecer la conexión WebSocket."""
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            # Iniciar el hilo para correr la conexión
            threading.Thread(target=self.ws.run_forever, daemon=True).start()
            time.sleep(2) # Esperar un poco para la conexión inicial
        except Exception as e:
            print(f"Error al conectar con Deriv: {e}")
            raise

    def _on_open(self, ws):
        """Se llama cuando la conexión está abierta. Autenticación."""
        print("Conexión con Deriv establecida. Autenticando...")
        self.authenticate()

    def _on_message(self, ws, message):
        """Procesa los mensajes recibidos del servidor."""
        data = json.loads(message)

        if 'msg_type' in data:
            if data['msg_type'] == 'authorize':
                print(f"Autenticación exitosa. Balance: {data['authorize']['balance']}")
            elif data['msg_type'] == 'buy':
                # Mensaje después de intentar comprar
                if 'buy' in data and data['buy']['status'] == 'Aceptado':
                    print("Orden de compra aceptada.")
                    self.subscribe_to_transaction(data['buy']['contract_id'])
                elif 'error' in data:
                    print(f"Error al comprar: {data['error']['message']}")
                    # Propagar el error para que sea capturado en ejecutar_trade
                    raise Exception(data['error']['message']) 
            elif data['msg_type'] == 'proposal_open_contract':
                # Mensaje de resultado (WIN/LOSS)
                is_valid = data['proposal_open_contract'].get('is_valid', 0)
                is_expired = data['proposal_open_contract'].get('is_expired', 0)
                status = data['proposal_open_contract'].get('status')
                
                if is_expired == 1 and is_valid == 1 and status == 'closed':
                    profit = data['proposal_open_contract']['profit']
                    if profit > 0:
                        self.on_trade_result("WIN")
                    else:
                        self.on_trade_result("LOSS")
                    # Deja de seguir el contrato
                    ws.send(json.dumps({"forget": data['proposal_open_contract']['contract_id']}))
            
            
    def _on_error(self, ws, error):
        """Maneja errores de WebSocket."""
        # Esto es crucial para que el 'except' en main.py fuerce el reinicio
        if "Connection is already closed" in str(error):
            raise ConnectionError("Connection is already closed")
        print(f"Error de conexión Deriv: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Se llama cuando la conexión se cierra."""
        print(f"Conexión con Deriv cerrada: {close_status_code} - {close_msg}")
        # Lanza un error al cerrar para forzar el manejo en main.py
        raise ConnectionError(f"Conexión cerrada: {close_msg}")

    def authenticate(self):
        """Envía el token para autenticación."""
        self.ws.send(json.dumps({"authorize": self.token}))

    def buy(self, symbol, contract_type, amount, duration):
        """Envía la solicitud de compra."""
        
        if contract_type.upper() == "BUY":
            contract_type = "CALL"
        elif contract_type.upper() == "SELL":
            contract_type = "PUT"
            
        payload = {
            "buy": 1,
            "price": amount,
            "parameters": {
                "amount": amount,
                "basis": "stake",
                "contract_type": contract_type,
                "currency": "USD",
                "duration": duration,
                "duration_unit": "m", # M = Minutes (para operar en M1)
                "symbol": symbol
            }
        }
        self.ws.send(json.dumps(payload))
        time.sleep(2) # Pausa para esperar la respuesta de la compra

    def subscribe_to_transaction(self, contract_id):
        """Suscribe al bot al resultado de un contrato."""
        self.ws.send(json.dumps({
            "proposal_open_contract": 1,
            "contract_id": contract_id,
            "subscribe": 1
        }))
