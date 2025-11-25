# =============================================================
#  RISK MANAGER — CryptoSniper v8.3
# =============================================================

from datetime import datetime
import pytz

mx = pytz.timezone("America/Mexico_City")


class RiskManager:

    def __init__(self, balance_inicial, max_loss_day, max_trades_day):
        self.balance_inicial = balance_inicial
        self.max_loss_day = max_loss_day
        self.max_trades_day = max_trades_day

        self.reset_diario()

    # ---------------------------------------------------------
    # Reset diario automático a las 00:00 MX
    # ---------------------------------------------------------
    def reset_diario(self):
        self.perdida_dia = 0
        self.trades_dia = 0
        self.ultimo_dia = datetime.now(mx).day

    # ---------------------------------------------------------
    # Registrar resultado real
    # ---------------------------------------------------------
    def registrar_resultado(self, profit):
        hoy = datetime.now(mx).day

        # Reset diario si cambia el día
        if hoy != self.ultimo_dia:
            self.reset_diario()

        if profit < 0:
            self.perdida_dia += abs(profit)

        self.trades_dia += 1

        print(f"[RISK] Resultado registrado: {profit}, Trades hoy: {self.trades_dia}")

    # ---------------------------------------------------------
    # Validar si se puede operar
    # ---------------------------------------------------------
    def puede_operar(self):
        hoy = datetime.now(mx).day

        if hoy != self.ultimo_dia:
            self.reset_diario()

        if self.perdida_dia >= self.max_loss_day:
            print("[RISK] ❌ Stop loss diario alcanzado.")
            return False

        if self.trades_dia >= self.max_trades_day:
            print("[RISK] ❌ Máximo de operaciones diarias alcanzado.")
            return False

        return True
