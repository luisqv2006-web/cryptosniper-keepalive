# =============================================================
# CRYPTOSNIPER FX — v8.0 HÍBRIDA PRO (AUTO RESULTADOS)
# Binarias 5M | AutoCopy + Risk Manager + Auto WIN/LOSS
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
# 🔥 ACTIVOS A OPERAR
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "BOOM500": "BOOM500",
    "CRASH500": "CRASH500",
    "STEP": "R_100"
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
# 🔌 CALLBACK PARA RESULTADOS (FORMATO A)
# ================================
def registrar_resultado(profit):
    resultado = "WIN" if profit > 0 else "LOSS"
    msg = f"🔔 {resultado}  ${profit:.2f}"
    send(msg)
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
    except:
        pass

# ================================
# 📊 OBTENER VELAS 5M
# ================================
def obtener_velas_5m(asset):
    symbol = SYMBOLS[asset]
    now = int(time.time())
    desde = now - (60 * 60 * 12)

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution=5&from={desde}&to={now}&token={FINNHUB_KEY}"
    r = requests.get(url).json()

    if r.get("s") != "ok":
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))

# ================================
# 🔍 DETECCIÓN ICT HÍBRIDA (SIMPLE)
# ================================
def detectar_confluencias(velas):
    o,h,l,c = zip(*[(x[1],x[2],x[3],x[4]) for x in velas[-12:]])

    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG_Internal": h[-2] < l[-4] or l[-2] > h[-4],
        "Liquidity_Internal": h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1]),
        "Volatilidad": statistics.mean([h[i] - l[i] for i in range(12)]) > 0.0009
    }

# ================================
# ✨ PROCESAR SEÑAL Y OPERAR
# ================================
def procesar_senal(asset, cons, price):

    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        return None
    
    if not risk.puede_operar():
        send("⚠ Límite diario alcanzado.")
        return

    symbol = SYMBOLS[asset]

    # Ejecutar REAL
    api.buy(symbol, direction, amount=1, duration=5)

    registrar_operacion(direction, price, "pendiente")

    return f"🚀 Operando {asset} | {direction} | {price}"

# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("🔥 CryptoSniper FX — Modo Híbrido Activado")
    ultimo_resumen = ""

    while True:
        ahora = datetime.now(mx)
        fecha = ahora.strftime("%Y-%m-%d")

        for asset in SYMBOLS.keys():

            velas = obtener_velas_5m(asset)
            if not velas:
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())
            price = velas[-1][4]

            if total == 3:
                send(f"📍 Setup en formación: {asset}")

            if total == 4:
                send(f"⚠ Señal fuerte en camino: {asset}")

            if total >= 5:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)

        if ahora.hour == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        time.sleep(300)

# ================================
# ▶ INICIAR
# ================================
threading.Thread(target=analizar).start()
