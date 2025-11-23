# =============================================================
# CRYPTOSNIPER FX — v8.0 MULTI-TF PROFESIONAL
# 5M señales → 1M confirma | SOLO FOREX + STEP | AutoCopy + Riesgo
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime
import statistics

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
# 🏦 ACTIVOS PERMITIDOS
# ================================
FOREX = ["EUR/USD", "GBP/USD", "USD/JPY"]
STEP = ["STEP", "STEP1S"]  # Mapeamos abajo

SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",

    "STEP": "R_100",
    "STEP1S": "1HZ100V",
}

# ================================
# 🛡 RISK MANAGER
# ================================
risk = RiskManager(balance_inicial=27, max_loss_day=5, max_trades_day=15)

# ================================
# 🤖 API + AUTOCOPY
# ================================
api = DerivAPI(DERIV_TOKEN)
copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=5)

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
# 🔎 FUNCIONES DE VELAS FINNHUB
# ================================
def obtener_velas(asset, timeframe):
    symbol = SYMBOLS[asset]
    now = int(time.time())
    desde = now - (60 * 60 * 12)

    url = f"https://finnhub.io/api/v1/forex/candle?symbol={symbol}&resolution={timeframe}&from={desde}&to={now}&token={FINNHUB_KEY}"
    r = requests.get(url).json()

    if r.get("s") != "ok":
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ================================
# 🔍 DETECCIÓN DE CONFLUENCIAS (5M)
# ================================
def detectar_confluencias(velas):
    o,h,l,c = zip(*[(x[1],x[2],x[3],x[4]) for x in velas[-12:]])

    return {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG": c[-1] > max(h[:-1])*1.0004 or c[-1] < min(l[:-1])*0.9996,
        "Volatilidad": statistics.mean([h[i] - l[i] for i in range(12)]) > 0.0009
    }


# ================================
# ✨ CONFIRMACIÓN EN 1M
# ================================
def confirmar_1m(asset, direction):
    velas = obtener_velas(asset, 1)
    if not velas: 
        return False

    o,h,l,c = zip(*[(x[1],x[2],x[3],x[4]) for x in velas[-5:]])

    if direction == "BUY":
        return c[-1] > o[-1] and l[-1] > l[-2]
    if direction == "SELL":
        return c[-1] < o[-1] and h[-1] < h[-2]

    return False


# ================================
# ⚡ PROCESAR SEÑAL FINAL
# ================================
def procesar_senal(asset, cons, price):

    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        return None
    
    if asset in FOREX or asset in STEP:
        if not confirmar_1m(asset, direction):
            print("[TF] ❌ 1M NO confirma.")
            return None

    if not risk.puede_operar():
        send("🚫 <b>Límite diario alcanzado</b>")
        return

    symbol = SYMBOLS[asset]

    api.buy(symbol, direction, amount=1, duration=5)
    registrar_operacion(direction, price, "pendiente")

    texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🔥 <b>OPERACIÓN EJECUTADA</b>

📌 Activo: {asset}
📈 Dirección: {direction}
💰 Monto: $1
🕒 Timeframe: 5M (Confirmado 1M)

🧩 Confluencias:
{texto}

🔍 Multi-TF: ACTIVADO
"""


# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("🚀 <b>CryptoSniper FX — v8.0 Multi-TF Activado</b>")
    ultimo_resumen = ""

    while True:
        ahora = datetime.now(mx)
        fecha = ahora.strftime("%Y-%m-%d")

        for asset in SYMBOLS.keys():
            velas5 = obtener_velas(asset, 5)
            if not velas5: continue

            cons = detectar_confluencias(velas5)
            total = sum(cons.values())
            price = velas5[-1][4]

            if total == 3:
                send(f"📍 Setup en formación\n{asset} | {total} confluencias.")
            if total == 4:
                send(f"⚠ Señal fuerte en camino\n{asset} | {total} confluencias.")

            if total >= 5:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)

        if ahora.hour == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        time.sleep(300)


# ================================
# ▶ INICIAR BOT
# ================================
threading.Thread(target=analizar).start()
