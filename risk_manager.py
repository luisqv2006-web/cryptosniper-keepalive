# =============================================================
# RISK MANAGER — CRYPTOSNIPER FX
# Control de pérdidas, trades diarios y balance lógico
# =============================================================

from datetime import datetime

class RiskManager:
    def __init__(self, balance_inicial=50, max_loss_day=10, max_trades_day=20):
        self.balance = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day

        self.perdida_hoy = 0
        self.trades_hoy = 0
        self.fecha = datetime.now().strftime("%Y-%m-%d")

    # --------------------------------------------
    # RESET DIARIO
    # --------------------------------------------
    def _reset_diario(self):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        if fecha_actual != self.fecha:
            print("[Risk] 🔄 Nuevo día, reiniciando límites.")
            self.fecha = fecha_actual
            self.perdida_hoy = 0
            self.trades_hoy = 0

    # --------------------------------------------
    # ¿SE PUEDE OPERAR?
    # --------------------------------------------
    def puede_operar(self):
        self._reset_diario()

        if self.perdida_hoy >= self.max_loss_day:
            print("[Risk] 🚫 Límite de pérdida diaria alcanzado.")
            return False
        
        if self.trades_hoy >= self.max_trades_day:
            print("[Risk] 🚫 Límite de operaciones diarias alcanzado.")
            return False
        
        return True

    # --------------------------------------------
    # REGISTRAR RESULTADO
    # --------------------------------------------
    def registrar_resultado(self, profit):
        self.trades_hoy += 1
        self.balance += profit
        if profit < 0:
            self.perdida_hoy += abs(profit)

        print(f"[Risk] Resultado: {profit} | Balance actual: {self.balance} | Pérdida hoy: {self.perdida_hoy}")
