class RiskManager:
    def __init__(self, balance_inicial, max_loss_day, max_trades_day):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day
        self.trades = 0
        self.losses = 0

    def registrar_perdida(self):
        self.losses += 1

    def registrar_trade(self):
        self.trades += 1

    def puede_operar(self):
        if self.losses >= self.max_loss_day:
            return False
        if self.trades >= self.max_trades_day:
            return False
        return True
