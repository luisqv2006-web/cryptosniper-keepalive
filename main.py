# =============================================================
# CRYPTOSNIPER FX — v11.0 SEMI-INSTITUCIONAL (BINARIAS 1M + 5M + ORO)
# ✅ SOLO EUR/USD + XAU/USD
# ✅ TWELVEDATA CORRECTO (SÍMBOLOS ARREGLADOS)
# ✅ SIN FINNHUB
# ✅ FLASK SOLO EN keep_alive.py
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
# 🔥 ACTIVOS (SOLO EUR/USD Y ORO)
# ✅ FORMATO CORRECTO PARA TWELVEDATA
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
# 📊 VELAS (TWELVEDATA ✅)
# ================================
def obtener_velas(asset, resol):
    symbol = SYMBOLS[asset]
    api_key = TWELVE_API_KEY

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={resol}min&outputsize=30&apikey={api_key}"

    try:
        r = requests.get(url, timeout=10).json()
    except Exception as e:
        send(f"⚠️ Error de red con TwelveData en {asset}: {e}")
        return None

    if "values" not in r:
        send(f"⚠️ TwelveData sin datos para {asset} | Respuesta: {r}")
        return None

    data = r["values"]
    data.reverse()

    velas = []
    for vela in data:
        velas.append((
            0,
            float(vela["open"]),
            float(vela["high"]),
            float(vela["low"]),
            float(vela["close"]),
            float(vela["volume"])
        ))

    return velas

# ================================
# 🔍 SEMI-INSTITUCIONAL
# ================================
def detectar_senal(v5, v1):
    o5, h5, l5, c5, v5v = zip(*v5[-10:])
    o1, h1, l1, c1, v1v = zip(*v1[-3:])

    contexto = c5[-1] > h5[-2] or c5[-1] < l5[-2]
    ruptura = c1[-2] > h1[-3] or c1[-2] < l1[-3]
    confirmacion = c1[-1] > c1[-2] if ruptura else False
    volumen = v1v[-1] > sum(v1v[-6:-1]) / 5

    return contexto and ruptura and confirmacion and volumen

# ================================
# ⏰ SESIÓN (24/7 ACTIVA)
# ================================
def sesion_activa():
    return True

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
    send("✅ BOT SEMI-INSTITUCIONAL ACTIVADO")
    actualizar_estado("Activo semi-institucional ✅")

    while True:
        try:
            send(f"🧠 Analizando EUR/USD y XAU/USD... {datetime.now(mx)}")

            if sesion_activa():
                for asset in SYMBOLS:
                    v5 = obtener_velas(asset, 5)
                    v1 = obtener_velas(asset, 1)

                    if not v5 or not v1:
                        continue

                    if detectar_senal(v5, v1):
                        price = v1[-1][4]
                        ejecutar_trade(asset, price)

            time.sleep(60)
        except Exception as e:
            send(f"⚠️ Error en loop: {e}")
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

    # Mantiene el proceso vivo
    while True:
        time.sleep(300)
