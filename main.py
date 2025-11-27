# =============================================================
# CRYPTOSNIPER FX — v10.1 PRO REAL (BINARIAS 1M GATILLO + 5M CONTEXTO)
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
# 📊 OBTENER VELAS 5M (CONTEXTO)
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
# 📊 OBTENER VELAS 1M (GATILLO)
# ================================
def obtener_velas_1m(asset):
    symbol = SYMBOLS[asset]
    now = int(time.time())
    desde = now - (60 * 60)

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution=1&from={desde}&to={now}&token={FINNHUB_KEY}"
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
# 🔍 CONTEXTO 5M + GATILLO 1M (BINARIAS)
# ================================
def detectar_confluencias(velas_5m, velas_1m):
    ohlc_5m = [(x[1], x[2], x[3], x[4]) for x in velas_5m[-10:]]
    ohlc_1m = [(x[1], x[2], x[3], x[4]) for x in velas_1m[-6:]]

    o5, h5, l5, c5 = zip(*ohlc_5m)
    o1, h1, l1, c1 = zip(*ohlc_1m)

    contexto = (c5[-1] > h5[-2]) or (c5[-1] < l5[-2])
    vela_fuerte = abs(c1[-1] - o1[-1]) > (h1[-1] - l1[-1]) * 0.6
    ruptura = (c1[-1] > h1[-2]) or (c1[-1] < l1[-2])

    return {
        "CONTEXTO": contexto,
        "GATILLO": vela_fuerte and ruptura
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
    direction = "BUY" if cons["GATILLO"] else "SELL"

    if not sesion_activa():
        return None

    tendencia = tendencia_macro(asset)
    if tendencia == "ALCISTA" and direction == "SELL":
        return None
    if tendencia == "BAJISTA" and direction == "BUY":
        return None

    if not risk.puede_operar():
        send("🛑 <b>Bot BLOQUEADO por riesgo</b>")
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
# 🔄 LOOP PRINCIPAL (ESCANEO 1 MINUTO)
# ================================
def analizar():
    send("🚀 <b>CryptoSniper FX PRO BINARIAS ACTIVADO</b>")
    actualizar_estado("Activo en REAL ✅")

    ultima_senal = datetime.now(mx)

    while True:
        for asset in SYMBOLS.keys():
            velas5m = obtener_velas(asset, "5m")
            velas1m = obtener_velas_1m(asset)

            if not velas5m or not velas1m:
                continue

            cons = detectar_confluencias(velas5m, velas1m)
            price = velas1m[-1][4]

            if cons["CONTEXTO"] and cons["GATILLO"]:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)
                    ultima_senal = datetime.now(mx)

        if datetime.now(mx) - ultima_senal >= timedelta(minutes=30):
            send("🧠 Bot activo y escaneando mercado…")
            actualizar_estado("Activo y analizando ✅")
            ultima_senal = datetime.now(mx)

        time.sleep(60)


# ================================
# ▶ INICIAR
# ================================
api = DerivAPI(DERIV_TOKEN, on_trade_result)
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
