class AutoCopy:
    def __init__(self, token, stake=1, duration=5):
        self.token = token
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction):
        print(f"[AUTOCOPY] Ejecutando {direction} en {symbol} con ${self.stake} por {self.duration}m")
