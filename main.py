from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import statistics
import pytz
from datetime import datetime, timedelta

from auto_copy import AutoCopy
from stats import registrar_operacion, resumen_diario
from risk_manager import RiskManager
from deriv_api import DerivAPI


TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")


SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "STEP": "R_100",
    "STEP1S": "1HZ100V"
}


risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15
)


def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except:
        pass


def obtener_velas(asset, timeframe):
    symbol = SYMBOLS[asset]
    now = int(time.time())

    resolutions = {
        "5m": 5,
        "15m": 15,
        "1h": 60
    }

    resol = resolutions[timeframe]
    desde = now - (60 * 60 * 24)

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution={resol}&from={desde}&to={now}&token={FINNHUB_KEY}"
    r = requests.get(url).json()

    if r.get("s") != "ok":
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


def ema(values, period):
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def tendencia_macro(asset):
    velas_h1 = obtener_velas(asset, "1h")
    velas_m15 = obtener_velas(asset, "15m")

    if not velas_h1 or not velas_m15:
        return None

    closes_h1 = [x[4] for x in velas_h1[-80:]]
    closes_m15 = [x[4] for x in velas_m15[-80:]]

    ema50_h1 = ema(closes_h1, 50)
    ema50_m15 = ema(closes_m15, 50)

    precio_h1 = closes_h1[-1]
    precio_m15 = closes_m15[-1]

    if precio_h1 > ema50_h1 and precio_m15 > ema50_m15:
        return "ALCISTA"
    if precio_h1 < ema50_h1 and precio_m15 < ema50_m15:
        return "BAJISTA"

    return "NEUTRA"


def detectar_confluencias(velas):
    o, h, l, c = zip(*[(x[1], x[2], x[3], x[4]) for x in velas[-12:]])

    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": h[-2] < l[-4] or l[-2] > h[-4],
        "Liquidez": h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1])
    }


def sesion_activa():
    hora = datetime.now(mx).hour
    return (2 <= hora <= 10) or (7 <= hora <= 14)


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
        return

    symbol = SYMBOLS[asset]
    api.buy(symbol, direction, amount=1, duration=5)

    registrar_operacion(direction, price, "pendiente")

    return f"""
🔥 Operación ejecutada  
📌 Activo: {asset}  
📈 Dirección: {direction}  
📊 Macro: {tendencia}  
⏳ TF: 5M  
"""


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

            if total == 3:
                send(f"📍 Setup en formación: {asset} ({total} confluencias)")

            if total >= 4:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)
                    ultima_senal = datetime.now(mx)

        if ahora.hour == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        if datetime.now(mx) - ultima_senal >= timedelta(hours=1):
            send("⏳ Analizando mercado...")
            ultima_senal = datetime.now(mx)

        time.sleep(300)


api = DerivAPI(DERIV_TOKEN, on_result_callback=lambda x: print("Resultado:", x))
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

threading.Thread(target=analizar).start()
