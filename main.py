# ------------------------------------
# CRYPTOSNIPER FX — ULTRA PRO REAL DATA v7.0
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

DERIV_TOKEN = "F2l44vScQP6FXKo"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")

NEWS_API = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_KEY}"


# ------------------------------------
# ACTIVOS (Deriv)
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "frxXAUUSD",
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
}

copy_trader = AutoCopy(DERIV_TOKEN)


# ------------------------------------
# TELEGRAM
# ------------------------------------
def send(msg):
    try:
        requests.post(TELEGRAM_API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        })
    except:
        pass


# ------------------------------------
# OBTENER VELAS 5M (REAL DATA)
# ------------------------------------
def obtener_velas_5m(symbol_key, cantidad=20):
    symbol = SYMBOLS[symbol_key]
    now = int(time.time())
    desde = now - (60 * 60 * 24)

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution=5&from={desde}&to={now}&token={FINNHUB_KEY}"
    )
    
    r = requests.get(url).json()
    if r.get("s") != "ok": 
        return None
    
    # devolvemos las últimas “cantidad” velas
    return list(zip(r["t"][-cantidad:], r["o"][-cantidad:], r["h"][-cantidad:], r["l"][-cantidad:], r["c"][-cantidad:]))


# ------------------------------------
# ICT — DETECCIÓN DE CONFLUENCIAS
# ------------------------------------
def detectar_confluencias(velas):
    o = [v[1] for v in velas]
    h = [v[2] for v in velas]
    l = [v[3] for v in velas]
    c = [v[4] for v in velas]

    cons = {
        "BOS": False,
        "CHOCH": False,
        "OrderBlock": False,
        "FVG_Internal": False,
        "FVG_External": False,
        "EQH": False,
        "EQL": False,
        "Liquidity": False,
        "Volatilidad": False,
        "Tendencia": False
    }

    # BOS / CHOCH
    if c[-1] > h[-2]: cons["BOS"] = True
    if c[-1] < l[-2]: cons["CHOCH"] = True

    # Order Block
    if (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]):
        cons["OrderBlock"] = True

    # FVG Interno
    if h[-2] < l[-4] or l[-2] > h[-4]:
        cons["FVG_Internal"] = True

    # FVG Externo
    if c[-1] > max(h[:-1])*1.0004 or c[-1] < min(l[:-1])*0.9996:
        cons["FVG_External"] = True

    # EQH / EQL
    if abs(h[-1] - h[-2]) < h[-1]*0.00015: cons["EQH"] = True
    if abs(l[-1] - l[-2]) < l[-1]*0.00015: cons["EQL"] = True

    # Liquidez
    if c[-1] > max(h[-10:-2]) or c[-1] < min(l[-10:-2]):
        cons["Liquidity"] = True

    # Volatilidad REAL
    rangos = [h[i] - l[i] for i in range(len(h))]
    if statistics.mean(rangos) > statistics.mean(rangos[:-5]) * 1.25:
        cons["Volatilidad"] = True

    # Tendencia REAL
    if abs(c[-1] - c[-5]) > (statistics.mean(rangos) * 0.5):
        cons["Tendencia"] = True

    return cons


# ------------------------------------
# PROCESAR SEÑAL (DERIV + ALERTA)
# ------------------------------------
def procesar_senal(pair, cons, price):

    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        return None

    simbolo = SYMBOLS[pair]
    copy_trader.ejecutar(simbolo, direction)

    texto = "\n".join([f"✔ {k}" for k, v in cons.items() if v])

    return f"""
🔥 <b>CryptoSniper FX — ULTRA PRO</b>

📌 Activo: {pair}
📈 Dirección: {direction}
💵 Precio actual: {price}

🧠 Confluencias reales:
{texto}

🤖 Operación automáticamente enviada a Deriv (5m)
"""


# ------------------------------------
# SESIONES
# ------------------------------------
def obtener_sesion(hora):
    if 2 <= hora < 10:
        return "Londres"
    elif 10 <= hora < 14:
        return "Overlap Londres + NY"
    elif 14 <= hora < 16:
        return "Nueva York"
    else:
        return "No Operativo"


# ------------------------------------
# LOOP PRINCIPAL (REAL DATA)
# ------------------------------------
def analizar():

    send("🔥 CryptoSniper FX — ULTRA PRO Activado (REAL DATA)")

    ultima_sesion = ""

    while True:

        ahora = datetime.now(mx)
        hora = ahora.hour

        # Sesiones
        sesion = obtener_sesion(hora)
        if sesion != ultima_sesion:
            send(f"🌍 Sesión actual: <b>{sesion}</b>")
            ultima_sesion = sesion

        if sesion == "No Operativo":
            time.sleep(300)
            continue

        # Análisis por par
        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas:
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())
            price = velas[-1][4]

            # PRE ALERTAS REALES (3–4)
            if 3 <= total < 5:
                texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])
                send(f"""
🟡 <b>PRE-ALERTA REAL ({total} Confirmaciones)</b>

📌 Activo: {pair}
💵 Precio: {price}

🧠 Señales encontradas:
{texto}

⏳ Aún no es entrada, pero se está alineando…
""")
                continue

            # SEÑAL COMPLETA ICT REAL (5+)
            if total >= 5:
                mensaje = procesar_senal(pair, cons, price)
                if mensaje:
                    send(mensaje)

        time.sleep(300)


# ------------------------------------
# INICIAR BOT
# ------------------------------------
threading.Thread(target=analizar).start()
