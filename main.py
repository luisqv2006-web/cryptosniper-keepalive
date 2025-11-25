# =============================================================
# CRYPTOSNIPER FX — v8.3 OPTIMIZADO (Render FREE)
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
# 🔧 CONFIGURACIÓN GENERAL
# ================================
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")

# ================================
# 🔥 ACTIVOS PERMITIDOS (3 para reducir RAM)
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
# 📩 ENVIAR TELEGRAM
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
# 🧠 CACHE DE VELAS
# ================================
cache = {
    "H1": {"time": 0, "data": None},
    "M15": {"time": 0, "data": None}
}

# ================================
# 📊 OBTENER VELAS (OPTIMIZADO)
# ================================
def obtener_velas(asset, timeframe):
    symbol = SYMBOLS[asset]
    now = int(time.time())

    resolutions = {"5m": 5, "15m": 15, "1h": 60}

    # ⏳ Velas necesarias solamente
    limit = 120  # suficiente para EMA 50 + ICT sin cargar miles de datos

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution={resolutions[timeframe]}"
        f"&count={limit}&token={FINNHUB_KEY}"
    )

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
# 📌 TENDENCIA MACRO OPTIMIZADA
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

    velas_h1 = cache["H1"]["data"]
    velas_m15 = cache["M15"]["data"]

    if not velas_h1 or not velas_m15:
        return None

    closes_h1 = [x[4] for x in velas_h1]
    closes_m15 = [x[4] for x in velas_m15]

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
# 🔍 ICT MICRO 5M
# ================================
def detectar_confluencias(velas):
    o, h, l, c = zip(*[(x[1], x[2], x[3], x[4]) for x in velas[-12:]])
    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock":
            (c[-1] > o[-1] and l[-1] > l[-2]) or
            (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": h[-2] < l[-4] or l[-2] > h[-4],
        "Liquidez": h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1])
    }

# ================================
# ⏰ SESIONES
# ================================
def sesion_activa():
    hora = datetime.now(mx).hour
    return (2 <= hora <= 10) or (7 <= hora <= 14)

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

    api.buy(SYMBOLS[asset], direction, amount=1, duration=5)
    registrar_operacion(direction, price, "pendiente")

    return f"""
🔥 Operación ejecutada  
📌 Activo: {asset}  
📈 Dirección: {direction}  
📊 Macro: {tendencia}  
⏳ TF: 5M  
"""

# ================================
# 🔄 LOOP PRINCIPAL (CADA 55 MIN)
# ================================
def analizar():
    send("🚀 CryptoSniper FX — v8.3 (Optimizado) Activado")
    ultimo_resumen = ""

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

            if total >= 4:   # sin alerta en 4, solo entrada
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)

        if ahora.hour == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        time.sleep(55 * 60)   # <— 55 minutos

# ================================
# ▶ INICIAR
# ================================
api = DerivAPI(DERIV_TOKEN, on_result_callback=lambda x: print("Resultado:", x))
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
