import datetime

class RiskManager:
    def __init__(self, balance_inicial=27, max_loss_day=5, max_trades_day=15):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day

        # Estado del día
        self.trades_realizados = 0
        self.perdidas_acumuladas = 0
        self.fecha_actual = datetime.date.today()

    def _reset_si_nuevo_dia(self):
        hoy = datetime.date.today()
        if hoy != self.fecha_actual:
            self.fecha_actual = hoy
            self.trades_realizados = 0
            self.perdidas_acumuladas = 0

    def registrar_resultado(self, profit):
        """
        Registra automáticamente el resultado de la operación.
        profit > 0 → win
        profit < 0 → loss
        """
        self._reset_si_nuevo_dia()
        self.trades_realizados += 1

        if profit < 0:
            self.perdidas_acumuladas += abs(profit)

    def puede_operar(self):
        """
        Verifica si el bot todavía puede operar hoy.
        """
        self._reset_si_nuevo_dia()

        if self.trades_realizados >= self.max_trades_day:
            print("[Risk] Bloqueo: Se alcanzó el límite de trades.")
            return False

        if self.perdidas_acumuladas >= self.max_loss_day:
            print("[Risk] Bloqueo: Se alcanzó el límite diario de pérdida.")
            return False

        return True
