# =============================================================
# AUTO COPY — Optimizado
# =============================================================

class AutoCopy:
    def __init__(self, token, stake=1, duration=5):
        self.token = token
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        pass  # ya no se usa porque main.py usa DerivAPI.buy()
