class RiskManager:
    def __init__(self, balance_inicial=100, max_loss_day=20, max_trades_day=10):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day
        
        self.trades_realizados = 0
        self.perdidas_acumuladas = 0

    def registrar_trade(self, ganancia):
        self.trades_realizados += 1
        self.perdidas_acumuladas += abs(min(ganancia, 0))

    def puede_operar(self):
        if self.trades_realizados >= self.max_trades_day:
            return False
        
        if self.perdidas_acumuladas >= self.max_loss_day:
            return False
        
        return True
