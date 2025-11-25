# =============================================================
# CRYPTOSNIPER FX — v8.4 ULTRA OPTIMIZADO (Render FREE)
# H1 + M15 + ICT | Scalping PRO | AutoCopy + Risk Manager
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime

from auto_copy import AutoCopy
from stats import registrar_operacion, resumen_diario
from risk_manager import RiskManager
from deriv_api import DerivAPI

# ================================
# 🔧 CONFIG GENERAL
# ================================
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

# ================================
# 🔥 ACTIVOS PERMITIDOS
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
        requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except:
        pass

# ================================
# 🧠 CACHE H1 / M15
# ================================
cache = {
    "H1": {"time": 0, "data": None},
    "M15": {"time": 0, "data": None}
}

# ================================
# 📊 OBTENER VELAS (OPT)
# ================================
def obtener_velas(asset, timeframe):
    symbol = SYMBOLS[asset]
    resolutions = {"5m": 5, "15m": 15, "1h": 60}
    limit = 120  # Súper liviano

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution={resolutions[timeframe]}&count={limit}&token={FINNHUB_KEY}"
    r = requests.get(url).json()

    if r.get("s") != "ok":
        return None
    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))

# ================================
# 📌 EMA
# ================================
def ema(values, period):
    if len(values) < period:
        return values[-1]
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e

# ================================
# 📌 MACRO TENDENCIA (CACHE)
# ================================
def tendencia_macro(asset):
    now = time.time()

    # H1 cada 30 min
    if now - cache["H1"]["time"] > 1800:
        cache["H1"]["data"] = obtener_velas(asset, "1h")
        cache["H1"]["time"] = now

    # M15 cada 15 min
    if now - cache["M15"]["time"] > 900:
        cache["M15"]["data"] = obtener_velas(asset, "15m")
        cache["M15"]["time"] = now

    h1 = cache["H1"]["data"]
    m15 = cache["M15"]["data"]
    if not h1 or not m15:
        return None

    closes_h1 = [x[4] for x in h1]
    closes_m15 = [x[4] for x in m15]

    ema50_h1 = ema(closes_h1, 50)
    ema50_m15 = ema(closes_m15, 50)

    p_h1 = closes_h1[-1]
    p_m15 = closes_m15[-1]

    if p_h1 > ema50_h1 and p_m15 > ema50_m15:
        return "ALCISTA"
    if p_h1 < ema50_h1 and p_m15 < ema50_m15:
        return "BAJISTA"
    return "NEUTRA"

# ================================
# 🔍 ICT 5M
# ================================
def detectar_confluencias(v):
    o, h, l, c = zip(*[(x[1], x[2], x[3], x[4]) for x in v[-12:]])
    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OB": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": h[-2] < l[-4] or l[-2] > h[-4]
    }

# ================================
# ⏰ SESIONES
# ================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 10) or (7 <= h <= 14)

# ================================
# ✨ PROCESAR SEÑAL
# ================================
def procesar_senal(asset, cons, price):
    direction = "BUY" if cons["BOS"] else "SELL" if cons["CHOCH"] else None
    if not direction:
        return None

    if not sesion_activa():
        return None

    macro = tendencia_macro(asset)
    if (macro == "ALCISTA" and direction == "SELL") or (macro == "BAJISTA" and direction == "BUY"):
        return None

    if not risk.puede_operar():
        send("⚠ Límite diario alcanzado.")
        return None

    api.buy(SYMBOLS[asset], direction, amount=1, duration=5)
    registrar_operacion(direction, price, "pendiente")

    return f"""
🔥 Operación ejecutada  
📌 {asset}  
📈 {direction}  
📊 Macro: {macro}  
⏳ 5M  
"""

# ================================
# 🔄 LOOP PRINCIPAL (55 min)
# ================================
def analizar():
    send("🚀 CryptoSniper FX — v8.4 OPTIMIZADO ACTIVADO")
    last = ""

    while True:
        now = datetime.now(mx)
        f = now.strftime("%Y-%m-%d")

        for asset in SYMBOLS.keys():
            v5 = obtener_velas(asset, "5m")
            if not v5:
                continue

            cons = detectar_confluencias(v5)
            total = sum(cons.values())
            price = v5[-1][4]

            if total >= 4:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)

        if now.hour == 22 and f != last:
            resumen_diario(send)
            last = f

        time.sleep(55 * 60)

# ================================
# ▶ INICIAR
# ================================
api = DerivAPI(DERIV_TOKEN, on_result_callback=lambda x: print("Resultado:", x))
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
