# ------------------------------------
# CRYPTOSNIPER FX — ULTRA PRO BINARIAS v6.1
# DEBUG ENVIADO AL GRUPO
# ------------------------------------

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


# ------------------------------------
# CONFIGURACIÓN
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"  # Grupo señales
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
NEWS_API = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_KEY}"

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")


# ------------------------------------
# ACTIVOS
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "frxXAUUSD",
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
}


# INICIALIZACIÓN
copy_trader = AutoCopy(DERIV_TOKEN, stake=5, duration=5)
risk = RiskManager(balance_inicial=100, max_loss_day=20, max_trades_day=10)


# ------------------------------------
# TELEGRAM
# ------------------------------------
def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except Exception as e:
        print("[Error Telegram]", e)


# ------------------------------------
# DEBUG -> AL GRUPO
# (para mandar logs importantes)
# ------------------------------------
def debug(msg):
    print("[DEBUG]", msg)
    send(f"🟣 DEBUG:\n{msg}")


# ------------------------------------
# OBTENER VELAS 5M
# ------------------------------------
def obtener_velas_5m(pair):
    symbol = SYMBOLS[pair]
    now = int(time.time())
    desde = now - (60 * 60 * 12)

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution=5&from={desde}&to={now}&token={FINNHUB_KEY}"
    )

    r = requests.get(url).json()
    if r.get("s") != "ok":
        debug(f"No hay velas para {pair}")
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ------------------------------------
# DETECCIÓN ICT
# ------------------------------------
def detectar_confluencias(velas):
    o,h,l,c = zip(*[(x[1],x[2],x[3],x[4]) for x in velas[-12:]])

    cons = {
        "BOS": c[-1] > h[-2],
        "CHOCH": c[-1] < l[-2],
        "OrderBlock": (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]),
        "FVG_Internal": h[-2] < l[-4] or l[-2] > h[-4],
        "FVG_External": c[-1] > max(h[:-1])*1.0004 or c[-1] < min(l[:-1])*0.9996,
        "EQH": abs(h[-1]-h[-2]) < (h[-1]*0.00015),
        "EQL": abs(l[-1]-l[-2]) < (l[-1]*0.00015),
        "Liquidity_Internal": h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1]),
        "Liquidity_External": c[-1] > max(h[-11:-3]) or c[-1] < min(l[-11:-3]),
        "Volatilidad": statistics.mean([h[i] - l[i] for i in range(12)]) > 0.0009,
        "Tendencia": c[-1] != c[-5]
    }

    return cons


# ------------------------------------
# EJECUTAR SEÑAL
# ------------------------------------
def procesar_senal(pair, cons, price):

    # Dirección
    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        debug(f"{pair} tiene confluencias pero no dirección → skip")
        return

    # Riesgo
    if not risk.puede_operar():
        debug("⚠ Límite diario alcanzado, operación cancelada")
        return

    simbolo = SYMBOLS[pair]

    copy_trader.ejecutar(simbolo, direction, amount=5)
    registrar_operacion(direction, price, result="pendiente")

    texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    send(f"""
🔥 *OPERACIÓN EJECUTADA*

📌 Par: {pair}
📈 Dirección: {direction}
💵 Precio: {price}
💰 Monto: $5

🧠 Confluencias:
{texto}
""")


# ------------------------------------
# LOOP PRINCIPAL
# ------------------------------------
def analizar():

    send("🚀 Bot activo — Enviando logs al grupo (DEBUG MODE)")
    ultimo_nivel = {}

    while True:
        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas: continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())

            # 🔍 LOG AL GRUPO
            debug(f"{pair} → {total} confluencias")

            # ALERTAS
            if total == 3:
                send(f"🟡 {pair} → 3 confluencias (posible setup)")

            if total == 4:
                send(f"🟠 {pair} → 4 confluencias (entrada inminente)")

            if total >= 5:
                price = velas[-1][4]
                procesar_senal(pair, cons, price)

        time.sleep(300)


# ------------------------------------
# START
# ------------------------------------
threading.Thread(target=analizar).start()
