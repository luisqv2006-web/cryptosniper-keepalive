# ------------------------------------
# CRYPTOSNIPER FX — ULTRA PRO BINARIAS v5.0
# Con AutoCopy + Pre-alertas + Telegram
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
# CONFIGURACIÓN TOKENS REALES
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"     # Bot Telegram
CHAT_ID = "-1003348348510"                                   # Canal
DERIV_TOKEN = "lit3a706U07EYMV"                              # Deriv real


# ------------------------------------
# API FINNHUB
# ------------------------------------
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


# Inicializa auto-operativa a $5
copy_trader = AutoCopy(DERIV_TOKEN, stake=5, duration=5)


# ------------------------------------
# ENVIAR MENSAJES
# ------------------------------------
def send(msg):
    requests.post(API, json={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    })


# ------------------------------------
# OBTENER VELAS 5M
# ------------------------------------
def obtener_velas_5m(symbol_key):
    symbol = SYMBOLS[symbol_key]
    now = int(time.time())
    desde = now - (60 * 60 * 6)

    url = (
        f"https://finnhub.io/api/v1/forex/candle?"
        f"symbol={symbol}&resolution=5&from={desde}&to={now}&token={FINNHUB_KEY}"
    )

    r = requests.get(url).json()
    if r.get("s") != "ok":
        return None
    return list(zip(r["t"], r["o"], r["h"], r["l"], r["c"]))


# ------------------------------------
# DETECTA CONFLUENCIAS ICT
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
        "Volatilidad": statistics.mean([h[i]-l[i] for i in range(12)]) > 0.0009,
        "Tendencia": c[-1] != c[-5]
    }

    return cons


# ------------------------------------
# NOTICIAS HIGH IMPACT
# ------------------------------------
def noticias_alto_impacto():
    data = requests.get(NEWS_API).json()
    eventos = data.get("economicCalendar", [])
    hoy = datetime.now(mx).strftime("%Y-%m-%d")
    
    return any(ev.get("impact") == "High" and ev.get("date") == hoy for ev in eventos)


# ------------------------------------
# PROCESAR SEÑAL
# ------------------------------------
def procesar_senal(pair, cons, price):

    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        return None

    simbolo_deriv = SYMBOLS[pair]

    # Ejecutar operación real
    copy_trader.ejecutar(simbolo_deriv, direction, amount=5)

    texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🔥✨ <b>CryptoSniper FX — OPERACIÓN ENVIADA</b>

📌 Activo: {pair}
📈 Dirección: {direction}
💰 Monto: $5
🧠 Confluencias:
{texto}

🤖 Ejecutado en Deriv (5m)
"""


# ------------------------------------
# LOOP PRINCIPAL
# ------------------------------------
def analizar():

    send("🔥 <b>CryptoSniper FX — ULTRA PRO ACTIVADO</b>")

    while True:

        # Filtro noticias
        if noticias_alto_impacto():
            send("🚨 Noticias High Impact | Pausa operativa")
            time.sleep(300)
            continue

        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas: 
                continue

            cons = detectar_confluencias(velas)
            total = sum(cons.values())

            # Pre-alerta exacta de 4
            if total == 4:
                send(f"⚠️ <b>Setup posible</b>\n📌 {pair}\n🧩 4 confluencias detectadas\n⏳ Monitoreando...")

            # Entrada real solo con 5+
            if total >= 5:
                price = velas[-1][4]
                mensaje = procesar_senal(pair, cons, price)
                if mensaje:
                    send(mensaje)

        time.sleep(300)



# ------------------------------------
# INICIAR
# ------------------------------------
threading.Thread(target=analizar).start()
