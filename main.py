# ------------------------------------
# CRYPTOSNIPER FX — ULTRA PRO BINARIAS v6.0
# Con AutoCopy, Risk Limit, Alertas 3-5, Stats
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
from risk_manager import RiskManager  # sin argumentos personalizados

# ------------------------------------
# CONFIGURACIÓN
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
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

# Inicializar AutoCopy (monto fijo)
copy_trader = AutoCopy(DERIV_TOKEN, stake=5, duration=5)

# Inicializar RiskManager (versión SIMPLE sin argumentos)
risk = RiskManager()

# ------------------------------------
# ENVIAR MENSAJE TELEGRAM
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
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ------------------------------------
# DETECCIÓN ICT CONFLUENCIAS
# ------------------------------------
def detectar_confluencias(velas):
    o,h,l,c = zip(*[(x[1],x[2],x[3],x[4]) for x in velas[-12:]])

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
    if abs(h[-1]-h[-2]) < (h[-1]*0.00015): cons["EQH"] = True
    if abs(l[-1]-l[-2]) < (l[-1]*0.00015): cons["EQL"] = True
    if h[-1] > max(h[-6:-1]) or l[-1] < min(l[-6:-1]): cons["Liquidity_Internal"] = True
    if c[-1] > max(h[-11:-3]) or c[-1] < min(l[-11:-3]): cons["Liquidity_External"] = True

    rng = [h[i] - l[i] for i in range(12)]
    if statistics.mean(rng) > 0.0009: cons["Volatilidad"] = True

    if c[-1] != c[-5]: cons["Tendencia"] = True

    return cons


# ------------------------------------
# NOTICIAS HIGH IMPACT
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
# PROCESAR SEÑAL + OPERAR
# ------------------------------------
def procesar_senal(pair, cons, price):

    # Determinar dirección
    if cons["BOS"]: direction = "BUY"
    elif cons["CHOCH"]: direction = "SELL"
    else:
        print("No hay dirección clara, skip")
        return None

    # Validar riesgo
    if not risk.puede_operar():
        send("🚫 Límite alcanzado. No operaré más hoy.")
        return None

    simbolo_deriv = SYMBOLS[pair]

    # Ejecutar orden
    copy_trader.ejecutar(simbolo_deriv, direction, amount=5)

    # Registrar operación (pendiente)
    registrar_operacion(direction, price, result="pendiente")

    confluencias_txt = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🔥 <b>Operación Ejecutada</b>

📌 Activo: {pair}
📈 Dirección: {direction}
💰 Monto: $5
🧠 Confluencias:
{confluencias_txt}

🤖 Orden enviada a Deriv
"""


# ------------------------------------
# LOOP PRINCIPAL
# ------------------------------------
def analizar():

    send("🔥 CryptoSniper FX — Activado ✔")
    ultimo_resumen = ""

    while True:

        ahora = datetime.now(mx)
        hora = ahora.hour
        fecha = ahora.strftime("%Y-%m-%d")

        # Pausar por noticias
        if noticias_alto_impacto():
            send("🚨 Noticias High Impact | Bot pausado temporalmente.")
            time.sleep(300)
            continue

        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas:
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())

            # Alertas
            if 3 <= total < 5:
                send(f"⚠ SETUP en formación | {pair} | {total} confluencias")

            if total == 4:
                send(f"🔥 Señal fuerte aproximándose | {pair}")

            # Entrada final
            if total >= 5:
                price = velas[-1][4]
                mensaje = procesar_senal(pair, cons, price)
                if mensaje:
                    send(mensaje)

        # Enviar resumen a las 10 PM
        if hora == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        time.sleep(300)


# ------------------------------------
# INICIAR BOT
# ------------------------------------
threading.Thread(target=analizar).start()
