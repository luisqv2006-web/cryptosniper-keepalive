# ------------------------------------
# CRYPTOSNIPER FX — ULTRA PRO BINARIAS v4.0
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

# ------------------------------------
# CONFIGURACIÓN
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"

# ⚠️ TU TOKEN ACTUAL DE DERIV
DERIV_TOKEN = "F2l44vScQP6FXKo"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
NEWS_API = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_KEY}"

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")

# ------------------------------------
# ACTIVOS (Deriv Symbols Reales)
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "frxXAUUSD",
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
}

# AutoCopy inicial
copy_trader = AutoCopy(DERIV_TOKEN)

# ------------------------------------
# MENSAJERÍA TELEGRAM
# ------------------------------------
def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except:
        pass


# ------------------------------------
# OBTENER VELAS 5M
# ------------------------------------
def obtener_velas_5m(symbol_key):
    symbol = SYMBOLS[symbol_key]
    now = int(time.time())
    desde = now - (60 * 60 * 12)

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution=5&from={desde}&to={now}&token={FINNHUB_KEY}"
    )

    r = requests.get(url).json()
    if r.get("s") != "ok":
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ------------------------------------
# DETECCIÓN ICT PRO ULTRA
# ------------------------------------
def detectar_confluencias(velas):
    o,h,l,c = zip(*[(x[1], x[2], x[3], x[4]) for x in velas[-12:]])

    cons = {
        "BOS": False,
        "CHOCH": False,
        "OrderBlock": False,
        "FVG_Internal": False,
        "FVG_External": False,
        "EQH": False,
        "EQL": False,
        "Liquidity_Internal": False,
        "Liquidity_External": False,
        "Volatilidad": False,
        "Tendencia": False
    }

    if c[-1] > h[-2]: cons["BOS"] = True
    if c[-1] < l[-2]: cons["CHOCH"] = True

    if (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]):
        cons["OrderBlock"] = True

    if h[-2] < l[-4] or l[-2] > h[-4]:
        cons["FVG_Internal"] = True

    if c[-1] > max(h[:-1])*1.0004 or c[-1] < min(l[:-1])*0.9996:
        cons["FVG_External"] = True

    if abs(h[-1] - h[-2]) < (h[-1] * 0.00015): cons["EQH"] = True
    if abs(l[-1] - l[-2]) < (l[-1] * 0.00015): cons["EQL"] = True

    if h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1]): cons["Liquidity_Internal"] = True
    if c[-1] > max(h[-11:-3]) or c[-1] < min(l[-11:-3]): cons["Liquidity_External"] = True

    rangos = [h[i] - l[i] for i in range(12)]
    if statistics.mean(rangos) > 0.0009:
        cons["Volatilidad"] = True

    if c[-1] > c[-5] or c[-1] < c[-5]:
        cons["Tendencia"] = True

    return cons  


# ------------------------------------
# NOTICIAS
# ------------------------------------
def noticias_alto_impacto():
    try:
        data = requests.get(NEWS_API).json()
        eventos = data.get("economicCalendar", [])
        hoy = datetime.now(mx).strftime("%Y-%m-%d")
        for ev in eventos:
            if ev.get("impact") == "High" and ev.get("date") == hoy:
                return True
    except:
        return False
    return False


# ------------------------------------
# SESIONES PRO
# ------------------------------------
def obtener_sesion(hora):
    if 2 <= hora < 10:
        return "Londres"
    elif 10 <= hora < 14:
        return "Overlap Londres - NY"
    elif 14 <= hora < 16:
        return "Nueva York"
    else:
        return "No Operativo"


# ------------------------------------
# PROCESAR SEÑAL + AUTOCOPY
# ------------------------------------
def procesar_senal(pair, cons, price):

    if cons["BOS"]: direction = "BUY"
    elif cons["CHOCH"]: direction = "SELL"
    else: return None
    
    simbolo_deriv = SYMBOLS[pair]

    copy_trader.ejecutar(simbolo_deriv, direction)

    texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🔥✨ <b>CryptoSniper FX — ULTRA PRO</b>

📌 <b>Activo:</b> {pair}
📈 <b>Dirección:</b> {direction}
💵 <b>Precio:</b> {price}

🧠 <b>Confluencias:</b>
{texto}

🤖 Operación ejecutada automáticamente en Deriv (5m)
"""


# ------------------------------------
# LOOP PRINCIPAL
# ------------------------------------
def analizar():

    send("🔥 <b>CryptoSniper FX — ULTRA PRO Activado</b>")
    ultima_sesion = ""

    while True:

        ahora = datetime.now(mx)
        hora = ahora.hour

        sesion = obtener_sesion(hora)
        if sesion != ultima_sesion:
            send(f"🌍 <b>Sesión actual:</b> {sesion}")
            ultima_sesion = sesion

        if sesion == "No Operativo":
            time.sleep(300)
            continue

        if noticias_alto_impacto():
            send("🚨 <b>Noticias High Impact — Operaciones pausadas</b>")
            time.sleep(300)
            continue

        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas:
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())
            price = velas[-1][4]

            # -----------------------------------------
            # 🔥 PRE-ALERTAS — 3 y 4 confluencias
            # -----------------------------------------
            if 3 <= total < 5:
                texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

                send(f"""
⚡ <b>PRE-ALERTA ICT ({total} confluencias)</b>

📌 Activo: {pair}
💵 Precio: {price}

🧠 Señales:
{texto}

⏳ Aún NO es entrada, pero el mercado se está cargando…
""")
                continue

            # -----------------------------------------
            # 🔥 OPERACIÓN — 5+
            # -----------------------------------------
            if total >= 5:
                mensaje = procesar_senal(pair, cons, price)
                if mensaje:
                    send(mensaje)

        time.sleep(300)


# ------------------------------------
# INICIAR BOT
# ------------------------------------
threading.Thread(target=analizar).start()
