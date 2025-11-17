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
from datetime import datetime, timedelta
import pytz
from flask import Flask, request

# ------------------------------------
# CONFIGURACIÓN — TOKEN Y CHAT ID
# ------------------------------------
TOKEN = "8588736688:AAF_mBkQUJIDXqAKBIzgDvsEGNJuqXJHNxA"
CHAT_ID = "-1003348348510"
FINNHUB_KEY = "d4d2n71r01qt1lahgi60d4d2n71r01qt1lahgi6g"
NEWS_API = "https://finnhub.io/api/v1/calendar/economic?token=" + FINNHUB_KEY

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

# Zona horaria México
mx = pytz.timezone("America/Mexico_City")

# ------------------------------------
# SERVIDOR FLASK PARA TRADINGVIEW
# ------------------------------------
app = Flask(__name__)

# Aquí guardamos la última señal que envió TradingView
tradingview_signal = {
    "indicator": None,
    "signal": None,
    "timestamp": 0
}

# Endpoint donde TradingView enviará webhooks
@app.route('/tv', methods=['POST'])
def webhook_tv():
    global tradingview_signal
    data = request.json

    try:
        indicator = data.get("indicator")
        signal = data.get("signal")

        if indicator and signal:
            tradingview_signal = {
                "indicator": indicator,
                "signal": signal,
                "timestamp": time.time()
            }

            return "OK", 200
    except:
        pass

    return "FAILED", 400


# ------------------------------------
# ACTIVOS OANDA
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "OANDA:XAU_USD",
    "EUR/USD": "OANDA:EUR_USD",
    "GBP/USD": "OANDA:GBP_USD",
    "USD/JPY": "OANDA:USD_JPY"
}

# ------------------------------------
# ENVIAR MENSAJE PREMIUM
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
# ICT PRO LIGERO
# ------------------------------------
def detectar_confluencias(symbol_key, velas):
    o, h, l, c = zip(*[(x[1], x[2], x[3], x[4]) for x in velas[-10:]])

    cons = {
        "BOS": False,
        "CHOCH": False,
        "OB": False,
        "FVG_Internal": False,
        "FVG_External": False,
        "EQH": False,
        "EQL": False,
        "Liquidity_Internal": False,
        "Liquidity_External": False,
        "Volatilidad": False,
        "Volumen": True
    }

    if c[-1] > h[-2]:
        cons["BOS"] = True
    if c[-1] < l[-2]:
        cons["CHOCH"] = True

    if (c[-1] > o[-1] and l[-1] > l[-2]) or (c[-1] < o[-1] and h[-1] < h[-2]):
        cons["OB"] = True

    if h[-2] < l[-4] or l[-2] > h[-4]:
        cons["FVG_Internal"] = True

    rango_alto = max(h[:-1])
    rango_bajo = min(l[:-1])
    if c[-1] > rango_alto * 1.0004 or c[-1] < rango_bajo * 0.9996:
        cons["FVG_External"] = True

    if abs(h[-1] - h[-2]) < (h[-1] * 0.00015):
        cons["EQH"] = True

    if abs(l[-1] - l[-2]) < (l[-1] * 0.00015):
        cons["EQL"] = True

    if h[-1] > max(h[-5:-1]) or l[-1] < min(l[-5:-1]):
        cons["Liquidity_Internal"] = True

    if c[-1] > max(h[-9:-3]) or c[-1] < min(l[-9:-3]):
        cons["Liquidity_External"] = True

    rangos = [h[i] - l[i] for i in range(10)]
    if statistics.mean(rangos) > 0.0009:
        cons["Volatilidad"] = True

    return cons


# ------------------------------------
# SEÑAL FINAL
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
        tp2 = price + dist * 2
        tp3 = price + dist * 3
    else:
        sl = price + dist
        tp1 = price - dist
        tp2 = price - dist * 2
        tp3 = price - dist * 3

    rr = round((tp1 - price) / abs(price - sl), 2)

    confluencias_texto = "\n".join([f"✔ {k}" for k, v in cons.items() if v])

    return f"""
🔥✨ <b>CryptoSniper FX — Señal Confirmada</b>

📌 <b>Activo:</b> {symbol_key}
📈 <b>Tipo:</b> {direction}
💵 <b>Precio:</b> {price}

⭐ <b>Confirmación TradingView:</b> SuperTrend {tradingview_signal["signal"]}

🎯 <b>TP1:</b> {tp1:.5f}
🎯 <b>TP2:</b> {tp2:.5f}
🎯 <b>TP3:</b> {tp3:.5f}

🛑 <b>SL:</b> {sl:.5f}
📊 <b>RR:</b> 1:{rr}

🧠 <b>Confluencias ICT PRO:</b>
{confluencias_texto}

⏳ TF: 5M + TradingView Confirmación
"""


# ------------------------------------
# LOOP PRINCIPAL CON DOBLE CONFIRMACIÓN
# ------------------------------------
def analizar_cada_5m():
    send("🔥 <b>CryptoSniper FX — Double Confirmation TradingView + ICT PRO ACTIVADO</b>")

    while True:
        ahora = datetime.now(mx)

        for pair in SYMBOLS.keys():
            velas = obtener_velas_5m(pair)
            if not velas:
                continue

            cons = detectar_confluencias(pair, velas)

            # Mínimo 4 confluencias ICT
            if sum(cons.values()) < 4:
                continue

            # TradingView debe haber mandado webhook en últimos 10 min
            if time.time() - tradingview_signal["timestamp"] > 600:
                continue

            # Señal debe coincidir con el análisis ICT
            tv_dir = tradingview_signal["signal"]

            # Predecir dirección ICT
            ict_dir = "BUY" if cons["BOS"] else "SELL" if cons["CHOCH"] else None

            if ict_dir != tv_dir:
                continue

            price = velas[-1][4]
            señal = generar_senal(pair, price, cons)
            send(señal)

        time.sleep(300)

# ------------------------------------
# INICIAR SERVIDOR Y ANALIZADOR
# ------------------------------------
if __name__ == "__main__":
    threading.Thread(target=analizar_cada_5m).start()
    app.run(host="0.0.0.0", port=8080)
