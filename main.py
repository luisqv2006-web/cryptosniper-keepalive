# =============================================================
# CRYPTOSNIPER FX — v8.3 (H1 + M15 + ICT + Sesiones)
# Scalping PRO | Forex + Step | AutoCopy + Risk Manager
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime, timedelta

from auto_copy import AutoCopy
from stats import registrar_operacion, resumen_diario
from risk_manager import RiskManager
from deriv_api import DerivAPI


# ================================
# 🔧 CONFIGURACIÓN GENERAL
# ================================
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")


# ================================
# 🔥 ACTIVOS A OPERAR
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "STEP": "R_100",
    "STEP1S": "1HZ100V"
}


# ================================
# 📌 RISK MANAGER (cuenta chica)
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15
)


# ================================
# 📩 ENVIAR MENSAJE TELEGRAM
# ================================
def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except:
        pass


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
# 📌 MACRO H1 + M15
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
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": h[-2] < l[-4] or l[-2] > h[-4],
        "Liquidez": h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1]),
    }


# ================================
# ⏰ SESIONES ACTIVAS
# ================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 10) or (7 <= h <= 14)


# ================================
# ✨ PROCESAR SEÑAL
# ================================
def procesar_senal(asset, cons, price):
    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        return None

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

    return (
        f"🔥 Operación ejecutada\n"
        f"📌 Activo: {asset}\n"
        f"📈 Dirección: {direction}\n"
        f"📊 Macro: {tendencia}\n"
        f"⏳ TF: 5M"
    )


# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("🚀 CryptoSniper FX — Versión 8.3 Activada")

    ultimo_resumen = ""
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

            if total >= 4:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)
                    ultima_senal = datetime.now(mx)

        if ahora.hour == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        if datetime.now(mx) - ultima_senal >= timedelta(minutes=55):
            send("🧠 El bot sigue analizando activamente el mercado…")
            ultima_senal = datetime.now(mx)

        time.sleep(300)


# ================================
# ▶ INICIAR
# ================================
api = DerivAPI(DERIV_TOKEN, on_result_callback=lambda x: print("Resultado:", x))
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
