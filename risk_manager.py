class RiskManager:

    def __init__(self, balance=100, risk_pct=1.0, max_trades=3):
        self.balance = balance
        self.risk_pct = risk_pct
        self.max_trades = max_trades
        self.active_trades = 0

    def calcular_lote(self):
        return round(self.balance * (self.risk_pct / 100), 2)

    def permitir_operacion(self):
        return self.active_trades < self.max_trades

    def abrir_trade(self):
        self.active_trades += 1
