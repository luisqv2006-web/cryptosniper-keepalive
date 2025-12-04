# =============================================================
# CRYPTOSNIPER FX — v15.0 IMMORTAL
# PRE-ALERTA + AUTO-ENTRADA | EUR/USD + XAU/USD
# SESIONES FUERTES | CADA 2 MIN
# AUTO-REINICIO + ALERTAS DE CAÍDA
# =============================================================

from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime
import os

from auto_copy import AutoCopy
from stats import registrar_operacion
from risk_manager import RiskManager
from deriv_api import DerivAPI
from firebase_cache import actualizar_estado, guardar_macro

# ================================
# 🔐 VARIABLES DE ENTORNO
# ================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

# ================================
# 🔥 ACTIVOS
# ================================
SYMBOLS = {
    "EUR/USD": "EUR/USD",
    "XAU/USD": "XAU/USD"
}

# ================================
# 📌 RISK MANAGER
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15
)

# ================================
# 📩 TELEGRAM
# ================================
def send(msg):
    try:
        requests.post(API, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
    except:
        pass

# ================================
# 🛡️ ANTI-CAÍDAS + AUTO-REINICIO
# ================================
ULTIMA_SEÑAL = time.time()

def actualizar_latido():
    global ULTIMA_SEÑAL
    ULTIMA_SEÑAL = time.time()

def watchdog():
    while True:
        try:
            diferencia = time.time() - ULTIMA_SEÑAL

            if diferencia > 360:  # 6 minutos sin vida → CRASH
                send("🔴 BOT CONGELADO — REINICIO AUTOMÁTICO ACTIVADO")
                time.sleep(3)
                os._exit(1)

            send("🟢 Bot vivo | Watchdog OK")
        except:
            pass

        time.sleep(300)  # Cada 5 minutos

# ================================
# 📊 RESULTADOS DERIV
# ================================
def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS registrado</b>")
        risk.registrar_perdida()

    registrar_operacion("AUTO", 0, result)

# ================================
# 📊 OBTENER VELAS
# ================================
def obtener_velas(asset, resol):
    symbol = SYMBOLS[asset]
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={resol}min&exchange=FOREX&outputsize=30&apikey={TWELVE_API_KEY}"

    try:
        r = requests.get(url, timeout=10).json()
    except:
        return None

    if "values" not in r:
        return None

    data = r["values"]
    data.reverse()

    velas = []
    for vela in data:
        try:
            o = float(vela["open"])
            h = float(vela["high"])
            l = float(vela["low"])
            c = float(vela["close"])
            v = float(vela["volume"]) if "volume" in vela else 1.0
            velas.append((o, h, l, c, v))
        except:
            continue

    return velas

# ================================
# 🔍 FASES
# ================================
def detectar_fase(v5, v1):
    try:
        o5, h5, l5, c5, v5v = zip(*v5[-10:])
        o1, h1, l1, c1, v1v = zip(*v1[-3:])

        contexto = c5[-1] > h5[-2] or c5[-1] < l5[-2]
        ruptura = c1[-2] > h1[-3] or c1[-2] < l1[-3]
        confirmacion = c1[-1] > c1[-2] if ruptura else False
        volumen = v1v[-1] > (sum(v1v[-3:]) / 3)

        if contexto and ruptura and not confirmacion:
            return "PRE"

        if contexto and ruptura and confirmacion and volumen:
            return "ENTRADA"

        return "NADA"

    except:
        return "NADA"

# ================================
# ⏰ SESIONES FUERTES
# ================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 5) or (7 <= h <= 10)

# ================================
# 🧠 PRE-ALERTAS
# ================================
prealertas = {}

# ================================
# 🚀 EJECUTAR TRADE
# ================================
def ejecutar_trade(asset, price):
    if not risk.puede_operar():
        send("🛑 Bot en pausa por racha negativa")
        return

    symbol = SYMBOLS[asset]
    direction = "BUY"

    api.buy(symbol, direction, amount=1, duration=1)
    risk.registrar_trade()

    guardar_macro({
        "activo": asset,
        "direccion": direction,
        "precio": price,
        "hora": str(datetime.now(mx))
    })

    send(f"🔴 <b>ENTRADA REAL</b>\n{asset}\n{direction}\n${price}")

# ================================
# 🔄 LOOP PRINCIPAL
# ================================
def analizar():
    send("✅ BOT ACTIVADO — AUTO-REINICIO + SILENCIO FUERA DE HORARIO")
    actualizar_estado("Activo con auto-reinicio ✅")

    while True:
        try:
            actualizar_latido()  # 🔥 clave para el watchdog

            if not sesion_activa():
                time.sleep(120)
                continue

            send(f"🧠 Analizando EUR/USD y XAU/USD... {datetime.now(mx)}")

            for asset in SYMBOLS:
                v5 = obtener_velas(asset, 5)
                v1 = obtener_velas(asset, 1)

                if not v5 or not v1:
                    continue

                fase = detectar_fase(v5, v1)
                precio_actual = v1[-1][3]

                if fase == "PRE" and not prealertas.get(asset):
                    send(f"🟡 <b>PRE-ALERTA</b>\n{asset}\nEsperando confirmación...")
                    prealertas[asset] = True

                if fase == "ENTRADA":
                    ejecutar_trade(asset, precio_actual)
                    prealertas[asset] = False

            time.sleep(120)

        except Exception as e:
            send(f"⚠️ Error crítico: {e}")
            time.sleep(30)

# ================================
# ▶ INICIO
# ================================
if __name__ == "__main__":
    api = DerivAPI(DERIV_TOKEN, on_trade_result)
    copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=1)

    hilo = threading.Thread(target=analizar)
    hilo.daemon = True
    hilo.start()

    hilo_watchdog = threading.Thread(target=watchdog)
    hilo_watchdog.daemon = True
    hilo_watchdog.start()

    while True:
        time.sleep(300)
