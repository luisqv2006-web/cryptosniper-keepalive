# ------------------------------------
# AUTO COPY — CRYPTOSNIPER FX (STAKE $5)
# Optimizado para Render / Producción
# ------------------------------------

from deriv_api import DerivAPI
import threading

class AutoCopy:
    def __init__(self, token, stake=5, duration=5):
        """
        token     -> Token de Deriv
        stake     -> Monto por operación (USD)
        duration  -> Minutos del contrato
        """
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration

    def ejecutar(self, symbol, direction, amount=None):
        """
        Ejecuta operación en Deriv en segundo plano.
        symbol    -> símbolo del activo (ej: frxEURUSD)
        direction -> BUY o SELL
        amount    -> monto opcional
        """
        monto = amount if amount is not None else self.stake

        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"[AutoCopy] → Enviando operación...")
        print(f"📌 Símbolo: {symbol}")
        print(f"📈 Dirección: {direction}")
        print(f"💵 Monto: ${monto}")
        print(f"⏱ Duración: {self.duration} minutos")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        thread = threading.Thread(
            target=self._send_order,
            args=(symbol, direction, monto)
        )
        thread.daemon = True
        thread.start()

    # ------------------------------------
    # PROCESAR ORDEN
    # ------------------------------------
    def _send_order(self, symbol, direction, monto):
        try:
            response = self.api.buy(
                symbol=symbol,
                direction=direction,
                amount=monto,
                duration=self.duration
            )

            print("[AutoCopy] ✔ Orden enviada correctamente.")
            print("[AutoCopy] 📤 Respuesta Broker:", response)

        except Exception as e:
            print("[AutoCopy] ❌ ERROR EN LA OPERACIÓN")
            print("Motivo:", e)
            print("────────────────────────────────────")
