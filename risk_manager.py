class RiskManager:
    def __init__(self):
        self.max_open_trades = 2
        self.default_lot = 0.35  # Riesgo bajo
        self.stop_loss_pips = 20
        self.take_profit_pips = 30

    def get_lot(self):
        return self.default_lot

    def can_open_trade(self, open_positions):
        return open_positions < self.max_open_trades
