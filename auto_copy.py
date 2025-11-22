# ------------------------------------
# AUTO COPY — USA MISMA API (SIN WS EXTRA)
# CRYPTOSNIPER FX v7.6
# ------------------------------------

class AutoCopy:
    def __init__(self, api, stake=1, duration=5):
        """
        api      -> Instancia de DerivAPI ya conectada
        stake    -> Monto por operación (USD)
        duration -> Duración del contrato (minutos)
        """
        self.api = api
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        """
        Ejecuta operación usando la API existente.
        No se abre nuevo WebSocket.
        """
        monto = amount if amount is not None else self.stake

        print(f"[AutoCopy] Ejecutando -> {direction} | {symbol} | ${monto}")

        try:
            self.api.buy(
                symbol,
                direction,
                amount=monto,
                duration=self.duration
            )
            print("[AutoCopy] ✔ Orden enviada correctamente a Deriv.")

        except Exception as e:
            print(f"[AutoCopy] ❌ Error al ejecutar operación:", e)
