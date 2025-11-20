# ------------------------------------
# AUTO COPY — CRYPTOSNIPER FX
# Manejo de ejecución de órdenes en Deriv
# ------------------------------------

from deriv_api import DerivAPI  # Asegúrate que tu clase DerivAPI esté en deriv_api.py

class AutoCopy:
    def __init__(self, token, stake=5, duration=5):
        """
        token   -> Token de Deriv
        stake   -> Monto por operación (USD)
        duration -> Duración del contrato en minutos
        """
        self.api = DerivAPI(token)
        self.stake = stake      # Monto fijo por defecto: $5
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        """
        Ejecuta una operación en Deriv.

        symbol    -> Símbolo de Deriv (ej: 'frxEURUSD')
        direction -> 'BUY' o 'SELL'
        amount    -> Monto opcional; si no se pasa, usa self.stake
        """
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] Enviando operación -> Símbolo: {symbol} | Dirección: {direction} | Monto: {monto}")

        try:
            # Usa la API de Deriv para enviar la orden
            self.api.buy(symbol, direction, monto, duration=self.duration)
            print("[AutoCopy] Operación enviada correctamente a Deriv.")
        except Exception as e:
            print(f"[AutoCopy] Error al ejecutar operación: {e}")
