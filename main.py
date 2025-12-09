# =============================================================
# CRYPTOSNIPER FX — v15.4 FINAL OPERATIVO (EMA 50 + Volumen Suave + Reset Diario)
# PRE-ALERTA + AUTO-ENTRADA | EUR/USD + XAU/USD
# SOLO HABLA EN HORARIO | AUTO-REINICIO + ALERTAS DE CAÍDA
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
# 📌 RISK MANAGER (Inicializado con zona horaria)
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15,
    timezone="America/Mexico_City"
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
# ⏰ SESIONES FUERTES (HORA MÉXICO)
# Londres: 02:00 – 05:00
# Nueva York: 07:00 – 10:00
# ================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 5) or (7 <= h <= 10)

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

            # 🔴 Si pasan 6 min sin actividad → reinicio forzado
            if diferencia > 360:
                send("🔴 BOT CONGELADO — REINICIO AUTOMÁTICO ACTIVADO")
                time.sleep(3)
                os._exit(1)

            # ✅ SOLO avisa que está vivo dentro del horario
            if sesion_activa():
                send("🟢 Bot vivo | Watchdog OK")

        except:
            pass

        time.sleep(300)  # cada 5 min

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
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={resol}min&exchange=FOREX&outputsize=100&apikey={TWELVE_API_KEY}" # Pedimos más velas para EMA 50

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
# 📐 CÁLCULO DE EMA
# ================================
def calcular_ema(candles, period):
    """Calcula la EMA de un conjunto de velas."""
    if len(candles) < period:
        return None
    
    # Extraemos solo los precios de cierre (índice 3)
    cierre = [c[3] for c in candles]

    # Constante de suavizado (K)
    k = 2 / (period + 1)
    
    # Primer valor de EMA es el SMA (Simple Moving Average)
    ema = sum(cierre[:period]) / period
    
    # Calcular EMA para el resto de los datos
    for price in cierre[period:]:
        ema = (price * k) + (ema * (1 - k))
        
    return ema

# ================================
# 🔍 DETECCIÓN DE FASES (EMA 50 + Volumen Suave)
# ================================
def detectar_fase(v5, v1):
    try:
        # Extraemos 10 velas de 5m para contexto
        o5, h5, l5, c5, v5v = zip(*v5[-10:])
        # Extraemos 3 velas de 1m para ruptura/confirmación
        o1, h1, l1, c1, v1v = zip(*v1[-3:]) 

        # 1. FILTRO DE TENDENCIA (EMA 50 en 5m)
        ema50 = calcular_ema(v5, 50)
        
        # Si no hay suficientes velas para la EMA, no operamos.
        if ema50 is None:
            return "NADA" 

        # Precio de Cierre actual de 5m
        precio_cierre_5m = c5[-1]
        
        # Determinamos la dirección y el contexto
        if precio_cierre_5m > ema50:
            # Tendencia alcista: solo buscamos BUY
            tendencia_ok = True
            direction = "BUY"
            
            # Contexto: Ruptura alcista
            contexto = precio_cierre_5m > h5[-2]
            
            # Ruptura en 1m: Vela [-2] rompe al alza
            ruptura = c1[-2] > h1[-3] 
            
            # Confirmación: Vela [-1] cierra al alza
            confirmacion = c1[-1] > c1[-2]
            
        elif precio_cierre_5m < ema50:
            # Tendencia bajista: solo buscamos SELL
            tendencia_ok = True
            direction = "SELL"
            
            # Contexto: Ruptura bajista
            contexto = precio_cierre_5m < l5[-2]
            
            # Ruptura en 1m: Vela [-2] rompe a la baja
            ruptura = c1[-2] < l1[-3] 
            
            # Confirmación: Vela [-1] cierra a la baja
            confirmacion = c1[-1] < c1[-2]
            
        else:
            # Precio cerca de la EMA o sin tendencia clara
            return "NADA" 
            
        # 2. FILTRO DE VOLUMEN SUAVE
        if len(v1) >= 10:
             # v1 es la lista completa de tuplas. Extraemos el volumen (índice 4) de las 9 velas anteriores de 1m
             volumenes_largos = [vela[4] for vela in v1[-10:-1]] 
             volumen_promedio_largo = sum(volumenes_largos) / 9
             volumen_actual = v1[-1][4]
             volumen_suficiente = volumen_actual > volumen_promedio_largo
        else:
             volumen_suficiente = False

        # 3. VERIFICACIÓN DE FASES
        if contexto and ruptura and not confirmacion and tendencia_ok:
            return "PRE", direction # Devolvemos la dirección junto con la fase

        if contexto and ruptura and confirmacion and volumen_suficiente and tendencia_ok: 
            return "ENTRADA", direction # Devolvemos la dirección junto con la fase

        return "NADA", None

    except:
        return "NADA", None

# ================================
# 🧠 PRE-ALERTAS
# ================================
prealertas = {}

# ================================
# 🚀 EJECUTAR TRADE
# ================================
def ejecutar_trade(asset, direction, price): # Acepta la dirección
    if not risk.puede_operar():
        send("🛑 Bot en pausa por racha negativa")
        return

    symbol = SYMBOLS[asset]
    # direction ya viene de detectar_fase

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
# 🔄 LOOP PRINCIPAL (SOLO EN HORARIO)
# ================================
def analizar():
    if sesion_activa():
        send("✅ BOT ACTIVADO — SOLO HABLA EN HORARIO")
        actualizar_estado("Activo modo horario ✅")

    while True:
        try:
            actualizar_latido()

            # 🔕 SILENCIO TOTAL FUERA DE HORARIO
            if not sesion_activa():
                time.sleep(120)
                continue

            send(f"🧠 Analizando EUR/USD y XAU/USD... {datetime.now(mx)}")

            for asset in SYMBOLS:
                v5 = obtener_velas(asset, 5)
                v1 = obtener_velas(asset, 1)

                # Aseguramos tener al menos 50 velas para calcular la EMA 50
                if not v5 or not v1 or len(v5) < 50: 
                    continue

                fase, direction = detectar_fase(v5, v1) # Recibe la dirección

                precio_actual = v1[-1][3]

                if fase == "PRE" and not prealertas.get(asset):
                    send(f"🟡 <b>PRE-ALERTA</b>\n{asset} | {direction}\nEsperando confirmación...")
                    prealertas[asset] = direction # Guardamos la dirección en la prealerta

                if fase == "ENTRADA":
                    # Usamos la dirección obtenida de la fase
                    ejecutar_trade(asset, direction, precio_actual) 
                    prealertas[asset] = None # Limpiamos la prealerta

            time.sleep(120)

        except Exception as e:
            if sesion_activa():
                send(f"⚠️ Error crítico: {e}")
            time.sleep(30)

# ================================
# ▶ INICIO (Manejo de Errores Críticos al inicio)
# ================================
if __name__ == "__main__":
    try:
        # 1. Inicializar APIs.
        api = DerivAPI(DERIV_TOKEN, on_trade_result)
        copy_trader = AutoCopy(DERIV_TOKEN, stake=1, duration=1)
        
        # Notificación de éxito
        send("✅ Conexión a Deriv exitosa. Iniciando hilos de análisis y watchdog.") 

        # 2. Iniciar hilos
        hilo = threading.Thread(target=analizar)
        hilo.daemon = True
        hilo.start()

        hilo_watchdog = threading.Thread(target=watchdog)
        hilo_watchdog.daemon = True
        hilo_watchdog.start()

    except Exception as e:
        # 3. Manejo de error crítico en el inicio
        error_msg = f"❌ ERROR CRÍTICO AL INICIAR: {e}. Bot detenido."
        print(error_msg)
        send(error_msg) 

    while True:
        time.sleep(300)
