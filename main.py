# ------------------------------------
# KEEP ALIVE — SERVIDOR 24/7
# ------------------------------------
from keep_alive import keep_alive
keep_alive()

import json
import time
import requests
import threading
import statistics
import os

# ------------------------------------
# CONFIGURACIÓN — (TU TOKEN Y CHAT ID)
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# ------------------------------------
# ACTIVOS (OANDA — Institucional)
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "OANDA:XAU_USD",
    "EUR/USD": "OANDA:EUR_USD",
    "GBP/USD": "OANDA:GBP_USD",
    "USD/JPY": "OANDA:USD_JPY"
}

# ------------------------------------
# ENVIAR MENSAJE A TELEGRAM
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
# OBTENER VELAS 5M DE FINNHUB
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
# DETECTAR CONFLUENCIAS INSTITUCIONALES
# ------------------------------------
def detectar_confluencias(symbol_key, velas):
    o,h,l,c = zip(*[(x[1], x[2], x[3], x[4]) for x in velas[-5:]])

    cons = {
        "BOS": False,
        "CHOCH": False,
        "OB": False,
        "FVG": False,
        "Liquidez": False,
        "Volumen": True,
        "Volatilidad": False
    }

    if c[-1] > h[-2]:
        cons["BOS"] = True
    if c[-1] < l[-2]:
        cons["CHOCH"] = True

    if (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]):
        cons["OB"] = True

    if h[-2] < l[-4] or l[-2] > h[-4]:
        cons["FVG"] = True

    if h[-1] > max(h[:-1]) or l[-1] < min(l[:-1]):
        cons["Liquidez"] = True

    rng = [h[i] - l[i] for i in range(5)]
    if statistics.mean(rng) > 0.0008:
        cons["Volatilidad"] = True

    return cons

# ------------------------------------
# GENERAR SEÑAL
# ------------------------------------
def generar_senal(symbol_key, price, cons):
    if cons["BOS"]:
        direction = "BUY"
    elif cons["CHOCH"]:
        direction = "SELL"
    else:
        direction = "BUY" if price % 2 == 0 else "SELL"

    dist = price * 0.0012

    if direction == "BUY":
        sl = price - dist
        tp1 = price + dist
        tp2 = price + dist*2
        tp3 = price + dist*3
    else:
        sl = price + dist
        tp1 = price - dist
        tp2 = price - dist*2
        tp3 = price - dist*3

    rr = round((tp1 - price) / abs(price - sl), 2)

    confluencias_texto = "\n".join([f"✔ {k}" for k,v in cons.items() if v])

    return f"""
🔥✨ <b>CryptoSniper FX — Señal Institucional</b>

📌 <b>Activo:</b> {symbol_key}
📈 <b>Tipo:</b> {direction}
💵 <b>Precio:</b> {price}

🎯 <b>TP1:</b> {tp1:.5f}
🎯 <b>TP2:</b> {tp2:.5f}
🎯 <b>TP3:</b> {tp3:.5f}

🛑 <b>SL:</b> {sl:.5f}
📊 <b>RR:</b> 1:{rr}

🧠 <b>Confluencias:</b>
{confluencias_texto}

⏳ TF: 5M (Vela cerrada)
"""

# ------------------------------------
# LOOP PRINCIPAL EN HILO
# ------------------------------------
def analizar_cada_5m():
    send("🔥 <b>CryptoSniper FX — Nivel 30 Premium Pro Activado</b>")

    while True:
        for pair in SYMBOLS.keys():
            velas = obtener_velas_5m(pair)
            if not velas:
                continue

            cons = detectar_confluencias(pair, velas)
            if sum(cons.values()) < 4:
                continue

            price = velas[-1][4]
            señal = generar_senal(pair, price, cons)
            send(señal)

        time.sleep(300)

# ------------------------------------
# INICIAR SISTEMA
# ------------------------------------
threading.Thread(target=analizar_cada_5m).start()
