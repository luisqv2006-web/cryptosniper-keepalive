from risk_manager import RiskManager

class AutoCopy:
    def __init__(self, api):
        self.api = api
        self.risk = RiskManager()

    def execute_trade(self, direction, symbol):
        lot = self.risk.get_lot()

        if direction == "BUY":
            return self.api.buy(symbol, lot)
        elif direction == "SELL":
            return self.api.sell(symbol, lot)

        return None
