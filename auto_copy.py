class AutoCopy:
    def __init__(self, token, stake=1, duration=1):
        self.token = token
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction):
        print(f"[AutoCopy REAL] {direction} en {symbol} por ${self.stake} a {self.duration}m")
