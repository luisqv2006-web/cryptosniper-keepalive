# =============================================================
# CRYPTOSNIPER FX — v7.6 HÍBRIDA PRO (AUTO RESULTADOS + BALANCE)
# Forex 5M | AutoCopy + Stats + Alertas Premium
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
from stats import registrar_resultado, obtener_balance
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
# 🔥 ACTIVOS A OPERAR (Forex)
# ================================
SYMBOLS = {
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY",
    "USD/CAD": "frxUSDCAD"
}

# ================================
# 📌 RISK MANAGER (modo conservador)
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=12
)

# ================================
# 🔌 API + CALLBACK RESULTADOS
# ================================
def callback_result(result, profit):
    # Registrar estadística
    registrar_resultado(result, profit)

    # Calcular balance virtual
    balance = obtener_balance()

    emoji = "🟢💰" if result == "WIN" else "🔴❌"

    send(f"""
{emoji} <b>{result} | {profit:.2f} USD</b>

💰 <b>Balance Total:</b> {balance:.2f} USD
📊 Estrategia ICT 5m | Confirmaciones 5+
🤖 Resultados automáticos desde Deriv
""")

# Conectar API
api = DerivAPI(DERIV_TOKEN, on_result=callback_result)

# AutoCopy con stake bajo
copy_trader = AutoCopy(api, stake=1, duration=5)

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
# 🔍 DETECCIÓN ICT HÍBRIDA
# ================================
def detectar_confluencias(velas):
    o,h,l,c = zip(*[(x[1],x[2],x[3],x[4]) for x in velas[-12:]])

    cons = {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG_Internal": h[-2] < l[-4] or l[-2] > h[-4],
        "FVG_External": c[-1] > max(h[:-1])*1.0004 or c[-1] < min(l[:-1])*0.9996,
        "Liquidity_Internal": h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1]),
        "Volatilidad": statistics.mean([h[i] - l[i] for i in range(12)]) > 0.0009
    }

    return cons


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
    
    if not risk.puede_operar():
        send("⚠ <b>Límite diario alcanzado.</b>")
        return

    symbol = SYMBOLS[asset]

    # Ejecutar operación real con DerivAPI
    api.buy(symbol, direction, amount=1, duration=5)

    texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🚀 <b>ENTRADA EJECUTADA</b>

📌 Activo: {asset}
📈 Dirección: {direction}
💰 Monto: $1
🕒 Timeframe: 5m

🧩 Confluencias:
{texto}

🤖 AutoCopy enviado a Deriv
"""


# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("🚀 <b>CryptoSniper FX — Monitoreando mercado...</b>")
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

            # Alertas previas
            if total == 3:
                send(f"📍 Setup en formación | {asset} | {total} confluencias.")
            if total == 4:
                send(f"⚡ Entrada inminente | {asset} | {total} confluencias.")

            # Entrada real
            if total >= 5:
                msg = procesar_senal(asset, cons, price)
                if msg:
                    send(msg)

        time.sleep(300)


# ================================
# ▶ INICIAR
# ================================
threading.Thread(target=analizar).start()
