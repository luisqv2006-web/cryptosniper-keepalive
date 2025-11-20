# ------------------------------------
# AUTO COPY — CRYPTOSNIPER FX (STAKE $5)
# ------------------------------------

from deriv_api import DerivAPI

class AutoCopy:
    def __init__(self, token, stake=5, duration=5):
        """
        token     -> Token de Deriv
        stake     -> Monto por operación (USD)
        duration  -> Minutos del contrato
        """
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        """
        Ejecuta una operación en Deriv.

        symbol    -> símbolo del activo en Deriv (ej: frxEURUSD)
        direction -> BUY o SELL
        amount    -> monto opcional
        """
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] Ejecutando -> Símbolo: {symbol} | Dirección: {direction} | Monto: ${monto}")

        try:
            # Enviar operación al broker
            self.api.buy(symbol, direction, monto, duration=self.duration)
            print("[AutoCopy] ✔ Orden enviada correctamente a Deriv.")
        except Exception as e:
            print(f"[AutoCopy] ❌ Error al ejecutar operación: {e}")
