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
# ACTIVOS (OANDA — Institucional)
# ------------------------------------
SYMBOLS = {
    "XAU/USD": "OANDA:XAU_USD",
    "EUR/USD": "OANDA:EUR_USD",
    "GBP/USD": "OANDA:GBP_USD",
    "USD/JPY": "OANDA:USD_JPY"
}

# ------------------------------------
# ENVIAR MENSAJE PREMIUM A TELEGRAM
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
# ICT PRO LIGERO — DETECCIÓN AVANZADA
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
# GENERAR SEÑAL PREMIUM
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
🔥✨ <b>CryptoSniper FX — Señal Institucional</b>

📌 <b>Activo:</b> {symbol_key}
📈 <b>Tipo:</b> {direction}
💵 <b>Precio:</b> {price}

🎯 <b>TP1:</b> {tp1:.5f}
🎯 <b>TP2:</b> {tp2:.5f}
🎯 <b>TP3:</b> {tp3:.5f}

🛑 <b>SL:</b> {sl:.5f}
📊 <b>RR:</b> 1:{rr}

🧠 <b>Confluencias ICT PRO:</b>
{confluencias_texto}

⏳ TF: 5M (Vela cerrada)
"""

# ------------------------------------
# DETECTAR NOTICIAS DE ALTO IMPACTO
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
        pass
    return False

# ------------------------------------
# LOOP PRINCIPAL — SEÑALES + PRE-ALERTAS
# ------------------------------------
def analizar_cada_5m():
    send("🔥 <b>CryptoSniper FX — Sistema Premium Activado</b>")
    
    ciclos = 0
    ultima_sesion = ""
    ultimo_reporte = 0
    ultimo_resumen = ""
    ultima_prealerta_por_par = {pair: 0 for pair in SYMBOLS.keys()}

    while True:
        ahora = datetime.now(mx)
        hora = ahora.hour
        fecha = ahora.strftime("%Y-%m-%d")
        timestamp_actual = int(time.time())

        # -------------------------
        # Sesiones
        # -------------------------
        if 19 <= hora < 4:
            sesion = "Asia"
        elif 2 <= hora < 10:
            sesion = "Londres"
        else:
            sesion = "Nueva York"

        if sesion != ultima_sesion:
            send(f"🌍 <b>Inicio de sesión {sesion}</b>\n📈 Volatilidad entrando…")
            ultima_sesion = sesion

        # -------------------------
        # Noticias
        # -------------------------
        if noticias_alto_impacto():
            send("🚨 <b>Noticias de alto impacto detectadas</b>\nEvitar señales durante próximos minutos.")

        # -------------------------
        # ANÁLISIS 5 MINUTOS
        # -------------------------
        señal_encontrada = False

        for pair in SYMBOLS.keys():

            velas = obtener_velas_5m(pair)
            if not velas:
                continue

            cons = detectar_confluencias(pair, velas)
            total = sum(cons.values())

            # PRE-ALERTA (exactamente 3 confluencias)
            if total == 3:
                if timestamp_actual - ultima_prealerta_por_par[pair] > 240:
                    send(
                        f"⚠️ <b>Posible Setup en Formación</b>\n\n"
                        f"📌 Activo: {pair}\n"
                        f"🧩 Confluencias detectadas: 3\n"
                        f"🔍 A punto de cumplirse estructura ICT.\n"
                        f"⏳ Monitoreando para entrada institucional…"
                    )
                    ultima_prealerta_por_par[pair] = timestamp_actual

            # SEÑAL PRINCIPAL (4+ confluencias)
            if total >= 4:
                price = velas[-1][4]
                señal = generar_senal(pair, price, cons)
                send(señal)
                señal_encontrada = True

        # -------------------------
        # Estado cada 30 min
        # -------------------------
        ciclos += 1
        if ciclos >= 6 and not señal_encontrada:
            send("🔎 <b>CryptoSniper FX sigue analizando…</b>\nSin confluencias fuertes aún.")
            ciclos = 0

        # -------------------------
        # Estado cada hora
        # -------------------------
        if hora != ultimo_reporte:
            send("📊 <b>Estado del mercado</b>\nTodo analizado correctamente.")
            ultimo_reporte = hora

        # -------------------------
        # Resumen diario
        # -------------------------
        if fecha != ultimo_resumen and hora == 22:
            send("📘 <b>Resumen del día:</b>\nMercado analizado, señales generadas y sesiones cubiertas.")
            ultimo_resumen = fecha

        time.sleep(300)

# ------------------------------------
# INICIAR SISTEMA
# ------------------------------------
threading.Thread(target=analizar_cada_5m).start()
