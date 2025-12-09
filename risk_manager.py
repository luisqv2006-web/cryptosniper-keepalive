import pytz
from datetime import datetime

class RiskManager:
    def __init__(self, balance_inicial, max_loss_day, max_trades_day, timezone):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day
        self.tz = pytz.timezone(timezone) 

        self.perdidas_hoy = 0
        self.trades_hoy = 0
        self.racha_perdidas = 0
        self.pausado = False
        self.fecha_ultimo_reset = datetime.now(self.tz).date() 

    def _check_and_reset_diario(self):
        """Revisa si es un nuevo día y resetea las métricas de riesgo."""
        today = datetime.now(self.tz).date()
        
        if today > self.fecha_ultimo_reset:
            # Si el día cambió, resetea los contadores
            self.perdidas_hoy = 0
            self.trades_hoy = 0
            self.racha_perdidas = 0
            self.pausado = False
            self.fecha_ultimo_reset = today

    def puede_operar(self):
        self._check_and_reset_diario() # Ejecuta el check diario antes de permitir operar
        
        if self.pausado:
            return False
        if self.perdidas_hoy >= self.max_loss_day:
            return False
        if self.trades_hoy >= self.max_trades_day:
            return False
        return True

    def registrar_trade(self):
        self.trades_hoy += 1

    def registrar_perdida(self):
        self.perdidas_hoy += 1
        self.racha_perdidas += 1

        if self.racha_perdidas == 2:
            self.pausado = True  # Pausa temporal
        if self.racha_perdidas >= 3:
            self.pausado = True  # Cierre total

    def registrar_win(self):
        self.racha_perdidas = 0
        self.pausado = False
