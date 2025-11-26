# =============================================================
# CRYPTOSNIPER FX — v8.4 Firebase Ultra Optimizado
# Análisis H1 + M15 + ICT 5M | AutoCopy | Risk | Cache Firebase
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime

from auto_copy import AutoCopy
from risk_manager import RiskManager
from deriv_api import DerivAPI
from firebase_cache import actualizar_estado, guardar_macro, obtener_macro

# ========================================
# CONFIG GENERAL
# ========================================
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")


# ========================================
# ACTIVOS
# ========================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
}


# ========================================
# TELEGRAM
# ========================================
def send(msg):
    try:
        requests.post(API, json={"chat_id": CHAT_ID, "text": msg})
    except:
        pass


# ========================================
# RISK MANAGER
# ========================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15
)


# ========================================
# OBTENER VELAS
# ========================================
def obtener_velas(asset, timeframe):
    symbol = SYMBOLS[asset]
    resolutions = {"5m": 5, "15m": 15, "1h": 60}

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution={resolutions[timeframe]}&count=120&token={FINNHUB_KEY}"
    )

    r = requests.get(url).json()
    if r.get("s") != "ok":
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ========================================
# EMA
# ========================================
def ema(values, period):
    if len(values) < period:
        return values[-1]
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


# ========================================
# TENDENCIA MACRO (cache por Firebase)
# ========================================
def tendencia_macro(asset):
    cache = obtener_macro(asset)
    if cache:
        return cache

    h1 = obtener_velas(asset, "1h")
    m15 = obtener_velas(asset, "15m")

    if not h1 or not m15:
        return None

    closes_h1 = [x[4] for x in h1]
    closes_m15 = [x[4] for x in m15]

    ema50_h1 = ema(closes_h1, 50)
    ema50_m15 = ema(closes_m15, 50)

    p_h1 = closes_h1[-1]
    p_m15 = closes_m15[-1]

    if p_h1 > ema50_h1 and p_m15 > ema50_m15:
        t = "ALCISTA"
    elif p_h1 < ema50_h1 and p_m15 < ema50_m15:
        t = "BAJISTA"
    else:
        t = "NEUTRA"

    guardar_macro(asset, t)
    return t


# ========================================
# ICT MICRO 5M
# ========================================
def detectar_confluencias(v):
    o, h, l, c = zip(*[(x[1], x[2], x[3], x[4]) for x in v[-12:]])

    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OB": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": h[-2] < l[-4] or l[-2] > h[-4]
    }


# ========================================
# SESIONES
# ========================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 10) or (7 <= h <= 14)


# ========================================
# PROCESAR SEÑAL
# ========================================
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

    api.buy(SYMBOLS[asset], direction, 1, 5)

    return f"""
🔥 Entrada Ejecutada
📌 Activo: {asset}
📈 Dirección: {direction}
📊 Macro: {macro}
⏳ TF: 5M
"""


# ========================================
# LOOP PRINCIPAL (cada 15 min)
# ========================================
def analizar():
    send("🚀 CryptoSniper FX — v8.4 Firebase ACTIVADO")
    actualizar_estado("Bot iniciado")

    while True:
        actualizar_estado("Analizando...")

        for asset in SYMBOLS.keys():
            velas = obtener_velas(asset, "5m")
            if not velas:
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())
            price = velas[-1][4]

            if total >= 4:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)
                    actualizar_estado("Señal enviada")

        time.sleep(900)  # 15 minutos


# ========================================
# INICIAR BOT
# ========================================
api = DerivAPI(DERIV_TOKEN, on_result_callback=lambda x: print("Resultado:", x))
threading.Thread(target=analizar).start()
