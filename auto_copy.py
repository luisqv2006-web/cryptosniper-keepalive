# ------------------------------------
# AUTO COPY — CRYPTOSNIPER FX (STAKE $5)
# ------------------------------------

from deriv_api import DerivAPI

class AutoCopy:
    def __init__(self, token, stake=5, duration=5):
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] Ejecutando operación → {symbol} | {direction} | ${monto}")

        try:
            self.api.buy(symbol, direction, monto, duration=self.duration)
        except Exception as e:
            print(f"[AutoCopy] Error: {e}")
