# ------------------------------------
# CRYPTOSNIPER FX — ULTRA PRO BINARIAS v5.0
# Con AutoCopy + Stats + Pre-alertas
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

# ------------------------------------
# CONFIGURACIÓN
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"  # Token del bot de Telegram
CHAT_ID = "-1003348348510"                                # Grupo o canal donde manda alertas

# 🔥 TOKEN REAL DE DERIV (ya actualizado)
DERIV_TOKEN = "lit3a706U07EYMV"

FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
NEWS_API = f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_KEY}"

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

mx = pytz.timezone("America/Mexico_City")

# ------------------------------------
# ACTIVOS (Deriv Symbols)
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "frxXAUUSD",
    "EUR/USD": "frxEURUSD",
    "GBP/USD": "frxGBPUSD",
    "USD/JPY": "frxUSDJPY"
}

# Inicializar AutoCopy ($5 por operación)
copy_trader = AutoCopy(DERIV_TOKEN, stake=5, duration=5)

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
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")


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
        print("⚠ Error obteniendo velas")
        return None

    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ------------------------------------
# DETECCIÓN ICT PRO ULTRA
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
# PROCESAR SEÑAL + AUTOCOPY
# ------------------------------------
def procesar_senal(pair, cons, price):

    if cons["BOS"]: direction = "BUY"
    elif cons["CHOCH"]: direction = "SELL"
    else: return None
    
    simbolo_deriv = SYMBOLS[pair]

    # Ejecutar operación
    copy_trader.ejecutar(simbolo_deriv, direction, amount=5)

    # Registrar operación
    registrar_operacion(direction, price, result="pendiente")

    texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🔥✨ <b>CryptoSniper FX — Operación Ejecutada</b>

📌 <b>Activo:</b> {pair}
📈 <b>Dirección:</b> {direction}
💵 <b>Precio:</b> {price}
💰 <b>Monto:</b> $5 USD

🧠 <b>Confluencias:</b>
{texto}

🤖 Orden enviada automáticamente a Deriv (5m)
"""


# ------------------------------------
# LOOP PRINCIPAL
# ------------------------------------
def analizar():

    send("🔥 <b>CryptoSniper FX — ULTRA PRO Activado</b>")
    ultimo_resumen = ""

    while True:
        print("⏳ Analizando mercados...")  # <-- Log para comprobar actividad

        ahora = datetime.now(mx)
        hora = ahora.hour
        fecha = ahora.strftime("%Y-%m-%d")

        # Noticias
        if noticias_alto_impacto():
            send("🚨 Noticias High Impact | Operaciones pausadas")
            time.sleep(300)
            continue

        # Revisar cada par
        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas: 
                print("⚠ Sin datos de velas, saltando...")
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())

            # PRE ALERTA (4 confluencias)
            if total == 4:
                send(f"⚠️ <b>SETUP EN FORMACIÓN</b>\n📌 {pair}\n🧩 4 confluencias detectadas\n⏳ Posible entrada pronto.")

            # OPERACIÓN COMPLETA (5+ confluencias)
            if total >= 5:
                price = velas[-1][4]
                mensaje = procesar_senal(pair, cons, price)
                if mensaje:
                    send(mensaje)

        # RESUMEN DIARIO 10PM
        if hora == 22 and fecha != ultimo_resumen:
            resumen_diario(send)
            ultimo_resumen = fecha

        time.sleep(300)


# ------------------------------------
# INICIAR BOT (CON HILO DAEMON)
# ------------------------------------
threading.Thread(target=analizar, daemon=True).start()
