# ------------------------------------
# AUTO COPY — CRYPTOSNIPER FX (STAKE $5)
# ------------------------------------

from deriv_api import DerivAPI  # Asegúrate que deriv_api.py está en el mismo directorio

class AutoCopy:
    def __init__(self, token, stake=5, duration=5):
        """
        token     -> Token de Deriv
        stake     -> Monto por operación (USD)
        duration  -> Duración del contrato en minutos
        """
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        """
        Ejecuta una operación en Deriv.

        symbol    -> Símbolo Deriv (ej: 'frxEURUSD')
        direction -> 'BUY' o 'SELL'
        amount    -> Monto personalizado; si no, usa stake
        """
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] → Ejecutando | Símbolo: {symbol} | Dirección: {direction} | Monto: ${monto}")

        try:
            self.api.buy(symbol, direction, monto, duration=self.duration)
            print("[AutoCopy] ✔ Orden enviada exitosamente.")
        except Exception as e:
            print(f"[AutoCopy] ❌ Error enviando operación: {e}")
