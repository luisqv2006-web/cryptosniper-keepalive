# ============================================
# RISK MANAGER — CryptoSniper FX (Cuenta Chica)
# Control diario de pérdidas, wins y operaciones
# ============================================

from datetime import datetime
import pytz

mx = pytz.timezone("America/Mexico_City")

class RiskManager:

    def __init__(self, balance_inicial=20, max_loss_day=5, max_trades_day=10):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day

        self.reset_diario()

    # ------------------------
    # RESET AUTOMÁTICO DIARIO
    # ------------------------
    def reset_diario(self):
        self.fecha = datetime.now(mx).strftime("%Y-%m-%d")
        self.trades_hoy = 0
        self.loss_acumulada = 0
        self.balance_actual = self.balance_inicial

    # ------------------------
    # VERIFICAR SI ES NUEVO DÍA
    # ------------------------
    def verificar_fecha(self):
        hoy = datetime.now(mx).strftime("%Y-%m-%d")
        if hoy != self.fecha:
            self.reset_diario()

    # ------------------------
    # ¿PUEDO OPERAR?
    # ------------------------
    def puede_operar(self):
        self.verificar_fecha()

        if self.loss_acumulada >= self.max_loss_day:
            return False

        if self.trades_hoy >= self.max_trades_day:
            return False

        return True

    # ------------------------
    # REGISTRAR RESULTADO REAL
    # ------------------------
    def registrar_resultado(self, profit):
        self.verificar_fecha()

        self.trades_hoy += 1
        self.balance_actual += profit

        if profit < 0:
            self.loss_acumulada += abs(profit)
