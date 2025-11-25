# =============================================================
# RISK MANAGER — Optimizado
# =============================================================

import json
import os
from datetime import datetime

class RiskManager:
    def __init__(self, balance_inicial, max_loss_day, max_trades_day):
        self.balance = balance_inicial
        self.max_loss = max_loss_day
        self.max_trades = max_trades_day

        self.trades_today = 0
        self.loss_today = 0
        self.day = datetime.now().strftime("%Y-%m-%d")

    def _reset_daily(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.day:
            self.day = today
            self.trades_today = 0
            self.loss_today = 0

    def puede_operar(self):
        self._reset_daily()
        if self.trades_today >= self.max_trades:
            return False
        if self.loss_today >= self.max_loss:
            return False
        return True

    def registrar_resultado(self, profit):
        self._reset_daily()
        self.trades_today += 1
        if profit < 0:
            self.loss_today += abs(profit)
