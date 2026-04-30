import pytz
from datetime import datetime, timedelta

class RiskManager:
    def __init__(self, balance_inicial, max_losses_day, max_trades_day, timezone, cooldown_minutos=30):
        self.balance_inicial = balance_inicial
        self.max_losses_day = max_losses_day
        self.max_trades_day = max_trades_day
        self.tz = pytz.timezone(timezone)
        self.cooldown = timedelta(minutes=cooldown_minutos)
        self.perdidas_hoy = 0
        self.trades_hoy = 0
        self.racha_perdidas = 0
        self.pausado_hasta = None
        self.fecha_ultimo_reset = datetime.now(self.tz).date()

    def _check_and_reset_diario(self):
        today = datetime.now(self.tz).date()
        if today > self.fecha_ultimo_reset:
            self.perdidas_hoy = 0
            self.trades_hoy = 0
            self.racha_perdidas = 0
            self.pausado_hasta = None
            self.fecha_ultimo_reset = today

    def puede_operar(self):
        self._check_and_reset_diario()
        ahora = datetime.now(self.tz)
        if self.pausado_hasta and ahora < self.pausado_hasta:
            return False
        if self.pausado_hasta and ahora >= self.pausado_hasta:
            self.pausado_hasta = None
            self.racha_perdidas = 0
        if self.perdidas_hoy >= self.max_losses_day:
            return False
        if self.trades_hoy >= self.max_trades_day:
            return False
        return True

    def registrar_trade(self):
        self.trades_hoy += 1

    def registrar_perdida(self):
        self.perdidas_hoy += 1
        self.racha_perdidas += 1
        if self.racha_perdidas >= 2:
            self.pausado_hasta = datetime.now(self.tz) + self.cooldown

    def registrar_win(self):
        self.racha_perdidas = 0
        self.pausado_hasta = None
