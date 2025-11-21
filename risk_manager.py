# ------------------------------------
# RISK MANAGER — CRYPTOSNIPER FX
# Límite de pérdidas, trades diarios y control básico
# ------------------------------------

from datetime import datetime

class RiskManager:
    def __init__(self, balance_inicial=100, max_loss_day=20, max_trades_day=10):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day

        self.reset_dia()

    # ------------------------------------
    # Reiniciar valores cada día
    # ------------------------------------
    def reset_dia(self):
        self.fecha = datetime.now().strftime("%Y-%m-%d")
        self.trades_realizados = 0
        self.perdidas_dia = 0

    # ------------------------------------
    # Validar si puede operar
    # ------------------------------------
    def puede_operar(self):
        hoy = datetime.now().strftime("%Y-%m-%d")

        # Si es nuevo día → reiniciar stats
        if hoy != self.fecha:
            self.reset_dia()

        if self.perdidas_dia >= self.max_loss_day:
            print("[RISK] ❌ Límite de pérdida alcanzado.")
            return False

        if self.trades_realizados >= self.max_trades_day:
            print("[RISK] ⚠ Límite de operaciones alcanzado.")
            return False

        return True

    # ------------------------------------
    # Registrar resultado después del trade
    # ------------------------------------
    def registrar_resultado(self, profit):
        self.trades_realizados += 1

        if profit < 0:
            self.perdidas_dia += abs(profit)

        print(f"[RISK] Día: {self.fecha} | Perdidas: {self.perdidas_dia} | Trades: {self.trades_realizados}")
