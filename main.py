# =============================================================
# CRYPTOSNIPER FX — v10.0 PRO REAL (SEÑALES + AUTOTRADING)
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
TOKEN = os.getenv("TELEGRAM_TOKEN", "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003348348510")
DERIV_TOKEN = os.getenv("DERIV_TOKEN", "lit3a706U07EYMV")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")


# ================================
# 🔥 PARES FOREX POPULARES
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "AUD/USD": "frxAUDUSD",
    "USD/CAD": "frxUSDCAD"
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
    except:
        pass


# ================================
# 📊 RESULTADOS DESDE DERIV
# ================================
def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
    else:
        send("❌ <b>LOSS registrado</b>")
        risk.registrar_perdida()

    registrar_operacion("AUTO", 0, result)


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

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))  # t,o,h,l,c


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
# 📌 TENDENCIA MACRO
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
# 🔍 ICT MICRO
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
        send("🛑 <b>Bot BLOQUEADO por límite de riesgo</b>")
        actualizar_estado("Bloqueado por riesgo ❌")
        return None

    symbol = SYMBOLS[asset]

    api.buy(symbol, direction, amount=1, duration=5)
    risk.registrar_trade()

    guardar_macro({
        "activo": asset,
        "direccion": direction,
        "precio": price,
        "hora": str(datetime.now(mx))
    })

    return (
        f"🔴 <b>EJECUCIÓN REAL</b>\n"
        f"📌 {asset}\n"
        f"📈 {direction}\n"
        f"💰 Precio: {price}\n"
        f"🧠 Macro: {tendencia}"
    )


# ================================
# 🔄 LOOP PRINCIPAL (CADA 1 MINUTO)
# ================================
def analizar():
    send("🚀 <b>CryptoSniper FX PRO REAL ACTIVADO</b>")
    actualizar_estado("Activo en REAL ✅")

    while True:
        for asset in SYMBOLS.keys():
            velas5m = obtener_velas(asset, "5m")
            if not velas5m:
                continue

            cons = detectar_confluencias(velas5m)
            total = sum(cons.values())
            price = velas5m[-1][4]

            if total == 3:
                send(
                    f"🟡 <b>PRE-ALERTA</b>\n"
                    f"📌 {asset}\n"
                    f"🧩 3 confluencias detectadas"
                )

            if total >= 4:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)

        # ✅ AHORA ANALIZA CADA 1 MINUTO
        time.sleep(60)


# ================================
# ▶ INICIAR
# ================================
api = DerivAPI(DERIV_TOKEN, on_trade_result)
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
