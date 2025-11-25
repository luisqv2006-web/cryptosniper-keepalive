# ============================================
# AUTO COPY — CryptoSniper FX (Deriv)
# Ejecuta contratos CALL/PUT automáticamente
# ============================================

from deriv_api import DerivAPI

class AutoCopy:
    def __init__(self, token, stake=1, duration=5):
        """
        token     -> Token de Deriv
        stake     -> Monto por operación (USD)
        duration  -> Duración en minutos del contrato
        """
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration

    # ------------------------------------
    # Ejecutar operación en Deriv
    # ------------------------------------
    def ejecutar(self, symbol, direction, amount=None):
        """
        Ejecuta un contrato CALL/PUT.

        symbol    -> Activo Deriv (ej: "frxEURUSD")
        direction -> BUY o SELL
        amount    -> monto opcional
        """

        monto = amount if amount is not None else self.stake

        try:
            self.api.buy(
                symbol,
                direction,
                amount=monto,
                duration=self.duration
            )
        except Exception as e:
            print(f"[AutoCopy] Error al ejecutar operación: {e}")
