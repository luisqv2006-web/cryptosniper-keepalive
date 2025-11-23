# =============================================================
# CRYPTOSNIPER FX — v8.2 (Tendencia Macro + Sesiones + Scalping 5M)
# Estrategia Híbrida | Forex + Step | AutoCopy + Risk Manager
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import statistics
import pytz
from datetime import datetime

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
# 🔥 ACTIVOS A OPERAR (Forex + Step)
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "STEP": "R_100",
    "STEP1S": "1HZ100V"
}


# ================================
# 📌 RISK MANAGER (cuenta pequeña)
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15
)


# ================================
# 🔌 CALLBACK RESULTADOS REALES
# ================================
def registrar_resultado(profit):
    resultado = "WIN" if profit > 0 else "LOSS"
    profit_fmt = f"{profit:.2f}"

    send(f"🎯 Resultado: <b>{resultado}</b> — ${profit_fmt}")
    risk.registrar_resultado(profit)


# ================================
# 🤖 API + AUTO COPY
# ================================
api = DerivAPI(DERIV_TOKEN, on_result_callback=registrar_resultado)
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)


# ================================
# 📩 ENVIAR MENSAJE
# ================================
def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print("[Error Telegram]", e)


# ================================
# 📊 OBTENER VELAS
# ================================
def obtener_velas(asset, timeframe="5m"):
    symbol = SYMBOLS[asset]
    now = int(time.time())

    resolutions = {"5m": 5, "1h": 60}
    resol = resolutions[timeframe]

    desde = now - (60 * 60 * 24)  # 24h de historial

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution={resol}&from={desde}&to={now}&token={FINNHUB_KEY}"
    r = requests.get(url).json()

    if r.get("s") != "ok":
        print("[WARN] No hay velas disponibles", symbol)
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ================================
# 📌 EMA (Tendencia Macro)
# ================================
def ema(values, period=50):
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def tendencia_h1(asset):
    velas = obtener_velas(asset, timeframe="1h")
    if not velas: return None

    closes = [x[4] for x in velas[-80:]]
    ema50 = ema(closes, 50)

    return "ALCISTA" if closes[-1] > ema50 else "BAJISTA"


# ================================
# 🔍 MICRO ESTRUCTURA (5M)
# ================================
def detectar_confluencias(velas):
    o, h, l, c = zip(*[(x[1], x[2], x[3], x[4]) for x in velas[-12:]])

    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": h[-2] < l[-4] or l[-2] > h[-4]
    }


# ================================
# ⏰ SESIONES (Filtro)
# Londres (2–10 MX) | NY (7–14 MX)
# ================================
def sesion_activa():
    hora = datetime.now(mx).hour
    return (2 <= hora <= 10) or (7 <= hora <= 14)


# ================================
# ✨ PROCESAR SEÑAL
# ================================
def procesar_senal(asset, cons, price):
    
    # Determinar dirección
    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        return None

    # 1️⃣ Sesiones
    if not sesion_activa():
        return None

    # 2️⃣ Macro Tendencia
    tendencia = tendencia_h1(asset)
    if tendencia == "ALCISTA" and direction == "SELL":
        return None
    if tendencia == "BAJISTA" and direction == "BUY":
        return None

    # 3️⃣ Riesgo
    if not risk.puede_operar():
        send("⚠ <b>Límite diario alcanzado</b>")
        return

    # 4️⃣ Enviar orden real
    api.buy(SYMBOLS[asset], direction, amount=1, duration=5)
    registrar_operacion(direction, price, "pendiente")

    return f"""
🔥 <b>OPERACIÓN ENVIADA</b>

📌 Activo: {asset}
📈 Dirección: {direction}
⌛ TF: 5M | Macro: {tendencia}
💰 Monto: $1
"""


# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("🚀 CryptoSniper FX — Versión v8.2 Activa")
    ultimo_resumen = ""

    while True:
        ahora = datetime.now(mx)
        fecha = ahora.strftime("%Y-%m-%d")

        for asset in SYMBOLS.keys():
            velas = obtener_velas(asset, "5m")
            if not velas: continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())
            price = velas[-1][4]

            if total == 3:
                send(f"📍 Setup formación | {asset} ({total} señales)")
            if total == 4:
                send(f"⚠ Setup fuerte | {asset} ({total} señales)")

            if total >= 5:
                msg = procesar_senal(asset, cons, price)
                if msg: send(msg)

        # Resumen diario
        if ahora.hour == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        time.sleep(300)


# ================================
# ▶ INICIAR BOT
# ================================
threading.Thread(target=analizar).start()
