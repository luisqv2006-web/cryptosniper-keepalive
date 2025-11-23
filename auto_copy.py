# =============================================================
# AUTO COPY — CRYPTOSNIPER FX
# Ejecuta contratos en Deriv usando WebSocket de DerivAPI
# =============================================================

from deriv_api import DerivAPI

class AutoCopy:
    def __init__(self, token, stake=1, duration=5):
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] Ejecutando: {symbol} | {direction} | ${monto}")

        try:
            self.api.buy(symbol, direction, monto, duration=self.duration)
            print("[AutoCopy] ✔ Orden enviada correctamente a Deriv.")
        except Exception as e:
            print(f"[AutoCopy] ❌ Error al ejecutar operación: {e}")
