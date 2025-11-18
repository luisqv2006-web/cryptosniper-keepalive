from deriv_api import DerivAPI
import time

class AutoCopy:

    def __init__(self, token):
        self.api = DerivAPI(token)
        self.loss_streak = 0
        self.stop_virtual = False

    def ejecutar(self, symbol, direction):
        if self.stop_virtual:
            return

        print(f"[AUTO-COPY] Ejecutando {direction} en {symbol}")
        self.api.buy(symbol, direction, amount=1)

    def registrar_perdida(self):
        self.loss_streak += 1
        if self.loss_streak >= 3:
            self.stop_virtual = True
            print("STOP VIRTUAL ACTIVADO (3 pérdidas seguidas)")

    def reset(self):
        self.loss_streak = 0
        self.stop_virtual = False
