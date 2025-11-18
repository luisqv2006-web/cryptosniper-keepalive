from deriv_api import DerivAPI
from risk_manager import RiskManager

MAP_SYMBOLS = {
    "XAU/USD": "frxXAUUSD",
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
}

class AutoCopy:

    def __init__(self, token):
        self.api = DerivAPI(token)
        self.risk = RiskManager()

    def ejecutar(self, pair, direction):
        if pair not in MAP_SYMBOLS:
            return

        symbol = MAP_SYMBOLS[pair]
        lote = self.risk.calcular_lote()

        if not self.risk.permitir_operacion():
            return

        self.api.buy(
            symbol=symbol,
            direction=direction,
            amount=lote,
            duration=5
        )

        self.risk.abrir_trade()
