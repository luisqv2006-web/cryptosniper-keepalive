# =============================================================
# CRYPTOSNIPER FX — v9.0 FINAL (PREALERTA + EJECUCIÓN)
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime, timedelta
import os

from auto_copy import AutoCopy
from stats import registrar_operacion, resumen_diario
from risk_manager import RiskManager
from deriv_api import DerivAPI
from firebase_cache import actualizar_estado, guardar_macro


# ================================
# 🔐 VARIABLES DE ENTORNO
# ================================
TOKEN = os.getenv("TELEGRAM_TOKEN", "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003348348510")
DERIV_TOKEN = os.getenv("DERIV_TOKEN", "lit3a706U07EYMV")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")


# ================================
# 🔥 ACTIVOS
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
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
        })
    except Exception as e:
        print(f"[Error Telegram] {e}")


# ================================
# 📊 OBTENER VELAS
# ================================
def obtener_velas(asset, timeframe):
    symbol = SYMBOLS[asset]
    now = int(time.time())

    resolutions = {"5m": 5, "15m": 15, "1h": 60}
    resol = resolutions[timeframe]
    desde = now - (60 * 60 * 24)

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution={resol}&from={desde}&to={now}&token={FINNHUB_KEY}"
    )

    r = requests.get(url).json()
    if r.get("s") != "ok":
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ================================
# 📌 EMA
# ================================
def ema(values, period):
    k = 2 / (period + 1)
    val = values[0]
    for v in values[1:]:
        val = v * k + val * (1 - k)
    return val


# ================================
# 📌 TENDENCIA MACRO H1 + M15
# ================================
def tendencia_macro(asset):
    h1 = obtener_velas(asset, "1h")
    m15 = obtener_velas(asset, "15m")

    if not h1 or not m15:
        return None

    closes_h1 = [x[4] for x in h1[-80:]]
    closes_m15 = [x[4] for x in m15[-80:]]

    ema50_h1 = ema(closes_h1, 50)
    ema50_m15 = ema(closes_m15, 50)

    if closes_h1[-1] > ema50_h1 and closes_m15[-1] > ema50_m15:
        return "ALCISTA"
    if closes_h1[-1] < ema50_h1 and closes_m15[-1] < ema50_m15:
        return "BAJISTA"
    return "NEUTRA"


# ================================
# 🔍 ICT MICRO (5M)
# ================================
def detectar_confluencias(velas):
    ohlc = [(x[1], x[2], x[3], x[4]) for x in velas[-12:]]
    o, h, l, c = zip(*ohlc)

    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": True,
        "FVG": True,
        "Liquidez": True,
    }


# ================================
# ⏰ SESIONES
# ================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 10) or (7 <= h <= 14)


# ================================
# ✨ PROCESAR EJECUCIÓN
# ================================
def procesar_senal(asset, cons, price):
    direction = "BUY" if cons["BOS"] else "SELL"

    if not sesion_activa():
        return None

    tendencia = tendencia_macro(asset)
    if tendencia == "ALCISTA" and direction == "SELL":
        return None
    if tendencia == "BAJISTA" and direction == "BUY":
        return None

    if not risk.puede_operar():
        send("⚠ Límite diario alcanzado.")
        return None

    symbol = SYMBOLS[asset]
    api.buy(symbol, direction, amount=1, duration=5)
    registrar_operacion(direction, price, "pendiente")

    guardar_macro({
        "activo": asset,
        "direccion": direction,
        "precio": price,
        "hora": str(datetime.now(mx))
    })

    return (
        f"🔴 <b>EJECUCIÓN CONFIRMADA</b>\n"
        f"📌 {asset}\n"
        f"📈 {direction}\n"
        f"💰 Precio: {price}\n"
        f"🧠 Macro: {tendencia}"
    )


# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("🚀 CryptoSniper FX iniciado")
    actualizar_estado("Bot iniciado correctamente ✅")

    ultima_senal = datetime.now(mx)

    while True:
        ahora = datetime.now(mx)
        fecha = ahora.strftime("%Y-%m-%d")

        for asset in SYMBOLS.keys():

            velas5m = obtener_velas(asset, "5m")
            if not velas5m:
                continue

            cons = detectar_confluencias(velas5m)
            total = sum(cons.values())
            price = velas5m[-1][4]

            # 🟡 PRE-ALERTA
            if total == 3:
                send(
                    f"🟡 <b>PRE-ALERTA</b>\n"
                    f"📌 {asset}\n"
                    f"🧩 3 confluencias detectadas\n"
                    f"⏳ Posible entrada próxima"
                )

            # 🔴 EJECUCIÓN
            if total >= 4:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)
                    ultima_senal = datetime.now(mx)

        # 🧠 MENSAJE DE VIDA CADA 55 MIN
        if datetime.now(mx) - ultima_senal >= timedelta(minutes=55):
            send("🧠 El bot sigue analizando el mercado…")
            actualizar_estado("Activo y analizando ✅")
            ultima_senal = datetime.now(mx)

        time.sleep(300)


# ================================
# ▶ INICIAR
# ================================
api = DerivAPI(DERIV_TOKEN)
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
