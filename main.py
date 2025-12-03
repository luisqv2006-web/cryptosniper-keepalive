# =============================================================
# CRYPTOSNIPER FX — v11.0 SEMI-INSTITUCIONAL (BINARIAS 1M + 5M + ORO)
# ✅ DEBUG DE FINNHUB + LOG DE ANÁLISIS + SESIÓN 24/7
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime
import os

from auto_copy import AutoCopy
from stats import registrar_operacion
from risk_manager import RiskManager
from deriv_api import DerivAPI
from firebase_cache import actualizar_estado, guardar_macro

# ================================
# 🔐 VARIABLES DE ENTORNO
# ================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
FINNHUB_KEY = os.getenv("FINNHUB_KEY")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

# ================================
# 🔥 ACTIVOS
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "USD/CAD": "frxUSDCAD",
    "XAU/USD": "frxXAUUSD"
}

# ================================
# 📌 RISK MANAGER
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15
)

# ================================
# 📩 TELEGRAM
# ================================
def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

# ================================
# 📊 RESULTADOS DERIV
# ================================
def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS registrado</b>")
        risk.registrar_perdida()

    registrar_operacion("AUTO", 0, result)

# ================================
# 📊 VELAS (CON ALERTA FINNHUB)
# ================================
def obtener_velas(asset, resol):
    symbol = SYMBOLS[asset]
    now = int(time.time())
    desde = now - 3600

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution={resol}&from={desde}&to={now}&token={FINNHUB_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
    except Exception as e:
        send(f"⚠️ Error de red con Finnhub en {asset}: {e}")
        return None

    if r.get("s") != "ok":
        send(f"⚠️ Finnhub sin datos para {asset} | Respuesta: {r}")
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"], r["v"]))

# ================================
# 🔍 SEMI-INSTITUCIONAL
# ================================
def detectar_senal(v5, v1):
    o5, h5, l5, c5, v5v = zip(*v5[-10:])
    o1, h1, l1, c1, v1v = zip(*v1[-3:])

    contexto = c5[-1] > h5[-2] or c5[-1] < l5[-2]
    ruptura = c1[-2] > h1[-3] or c1[-2] < l1[-3]
    confirmacion = c1[-1] > c1[-2] if ruptura else False
    volumen = v1v[-1] > sum(v1v[-6:-1]) / 5

    return contexto and ruptura and confirmacion and volumen

# ================================
# ⏰ SESIÓN (DESBLOQUEADA 24/7 PARA PRUEBA)
# ================================
def sesion_activa():
    return True

# ================================
# 🚀 EJECUTAR TRADE
# ================================
def ejecutar_trade(asset, price):
    if not risk.puede_operar():
        send("🛑 Bot en pausa por racha negativa")
        return

    symbol = SYMBOLS[asset]
    direction = "BUY"

    api.buy(symbol, direction, amount=1, duration=1)
    risk.registrar_trade()

    guardar_macro({
        "activo": asset,
        "direccion": direction,
        "precio": price,
        "hora": str(datetime.now(mx))
    })

    send(f"🔴 <b>ENTRADA REAL</b>\n{asset}\n{direction}\n${price}")

# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("✅ BOT SEMI-INSTITUCIONAL ACTIVADO")
    actualizar_estado("Activo semi-institucional ✅")

    while True:
        try:
            send(f"🧠 Analizando mercado... {datetime.now(mx)}")

            if sesion_activa():
                for asset in SYMBOLS:
                    v5 = obtener_velas(asset, 5)
                    v1 = obtener_velas(asset, 1)

                    if not v5 or not v1:
                        continue

                    if detectar_senal(v5, v1):
                        price = v1[-1][4]
                        ejecutar_trade(asset, price)

            time.sleep(60)
        except Exception as e:
            send(f"⚠️ Error en loop: {e}")
            time.sleep(30)

# ================================
# ▶ INICIO
# ================================
if __name__ == "__main__":
    api = DerivAPI(DERIV_TOKEN, on_trade_result)
    copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=1)

    hilo = threading.Thread(target=analizar)
    hilo.daemon = True
    hilo.start()

    # Mantiene el proceso vivo
    while True:
        time.sleep(300)
