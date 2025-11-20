# ------------------------------------
# AUTO COPY — CRYPTOSNIPER FX (STAKE $5 + RESULTADOS)
# ------------------------------------

from deriv_api import DerivAPI

class AutoCopy:
    def __init__(self, token, stake=5, duration=5, send_callback=None):
        """
        token        -> Token de Deriv
        stake        -> Monto por operación (USD)
        duration     -> Duración en minutos
        send_callback -> Función para mandar mensajes a Telegram
        """
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration
        self.send_callback = send_callback

        # 🔥 Escuchamos resultados de Deriv
        self.api.on_result = self._handle_result

    # ------------------------------------
    # EJECUTAR ORDEN
    # ------------------------------------
    def ejecutar(self, symbol, direction, amount=None):
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] Enviando operación -> {symbol} | {direction} | ${monto}")

        try:
            self.api.buy(symbol, direction, monto, duration=self.duration)
            print("[AutoCopy] ✔ Orden enviada correctamente.")
        except Exception as e:
            print(f"[AutoCopy] ❌ Error al enviar operación: {e}")

    # ------------------------------------
    # RESULTADOS DEL CONTRATO
    # ------------------------------------
    def _handle_result(self, data):
        """Recibe WIN/LOSS desde DerivAPI"""
        cid = data["contract_id"]
        result = data["result"]
        profit = round(data["profit"], 2)

        mensaje = f"""
📊 <b>Resultado Operación</b>
🆔 ID: <code>{cid}</code>
📌 Resultado: <b>{result}</b>
💰 Ganancia: <b>${profit}</b>
"""

        print("[AutoCopy] 📌 Resultado recibido:", result, profit)

        if self.send_callback:
            self.send_callback(mensaje)
