# =============================================================
# CRYPTOSNIPER FX — v15.8 FINAL OPERATIVO (ESTABILIDAD + FRECUENCIA)
# SIN FILTRO DE VOLUMEN en la entrada. RECONEXIÓN AUTOMÁTICA.
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
# 📌 RISK MANAGER (Inicializado con zona horaria para reseteo diario)
# ================================
risk = RiskManager(
    balance_inicial=27,
    max_loss_day=5,
    max_trades_day=15,
    timezone="America/Mexico_City" # Se añade la zona horaria
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
    # Se piden 100 velas para calcular correctamente la EMA 50 y el RSI 14
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={resol}min&exchange=FOREX&outputsize=100&apikey={TWELVE_API_KEY}" 

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
# 📐 CÁLCULO DE INDICADORES
# ================================
def calcular_ema(candles, period):
    if len(candles) < period:
        return None
    cierre = [c[3] for c in candles]
    k = 2 / (period + 1)
    ema = sum(cierre[:period]) / period
    for price in cierre[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calcular_rsi(candles, period=14):
    if len(candles) < period + 1:
        return None
        
    cierres = [c[3] for c in candles]
    
    ganancias = []
    perdidas = []
    
    for i in range(1, len(cierres)):
        cambio = cierres[i] - cierres[i-1]
        ganancias.append(max(0, cambio))
        perdidas.append(max(0, -cambio))

    avg_gain = sum(ganancias[:period]) / period
    avg_loss = sum(perdidas[:period]) / period
    
    for i in range(period, len(ganancias)):
        avg_gain = (avg_gain * (period - 1) + ganancias[i]) / period
        avg_loss = (avg_loss * (period - 1) + perdidas[i]) / period
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ================================
# 🔍 DETECCIÓN DE FASES (VOLUMEN ELIMINADO DE LA ENTRADA)
# ================================
def detectar_fase(v5, v1):
    try:
        # Extraemos las velas necesarias
        o5, h5, l5, c5, v5v = zip(*v5[-10:])
        o1, h1, l1, c1, v1v = zip(*v1[-3:]) 

        # 1. FILTRO DE TENDENCIA (EMA 50 en 5m)
        ema50 = calcular_ema(v5, 50)
        
        if ema50 is None:
            return "NADA", None 

        precio_cierre_5m = c5[-1]
        
        # 2. FILTRO DE FUERZA (RSI 14 en 1m)
        rsi14 = calcular_rsi(v1, 14)
        if rsi14 is None:
            return "NADA", None
            
        # 3. Lógica de Dirección
        if precio_cierre_5m > ema50:
            direction = "BUY"
            
            # FILTRO RSI: No sobrecomprado (RSI < 70)
            if rsi14 >= 70:
                return "NADA", None 
            
            # Contexto/Ruptura/Confirmación
            contexto = precio_cierre_5m > h5[-2]
            ruptura = c1[-2] > h1[-3] 
            confirmacion = c1[-1] > c1[-2]
            
        elif precio_cierre_5m < ema50:
            direction = "SELL"
            
            # FILTRO RSI: No sobrevendido (RSI > 30)
            if rsi14 <= 30:
                return "NADA", None
            
            # Contexto/Ruptura/Confirmación
            contexto = precio_cierre_5m < l5[-2]
            ruptura = c1[-2] < l1[-3] 
            confirmacion = c1[-1] < c1[-2]
            
        else:
            return "NADA", None
            
        # 4. FILTRO DE VOLUMEN SUAVE (Calculado pero IGNORADO en la ENTRADA)
        # Se mantiene el código de volumen para referencia, pero se ignora.
        if len(v1) >= 10:
             volumenes_largos = [vela[4] for vela in v1[-10:-1]] 
             volumen_promedio_largo = sum(volumenes_largos) / 9
             volumen_actual = v1[-1][4]
             volumen_suficiente = volumen_actual > volumen_promedio_largo
        else:
             volumen_suficiente = False

        # 5. VERIFICACIÓN DE FASES
        if contexto and ruptura and not confirmacion:
            return "PRE", direction 

        # AHORA SOLO REQUIERE CONTEXTO, RUPTURA Y CONFIRMACIÓN. (VOLUMEN ELIMINADO)
        if contexto and ruptura and confirmacion: 
            return "ENTRADA", direction 

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
def ejecutar_trade(asset, direction, price):
    if not risk.puede_operar():
        send("🛑 Bot en pausa por racha negativa")
        return

    symbol = SYMBOLS[asset]

    # La función api.buy debe estar definida en deriv_api.py y debe manejar la dirección
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
    # Este mensaje solo se envía si el bot inicia DENTRO de horario
    if sesion_activa():
        send("✅ BOT ACTIVADO — SOLO HABLA EN HORARIO")
        actualizar_estado("Activo modo horario ✅")

    while True:
        try:
            actualizar_latido()

            if sesion_activa():
                # 🧠 MODO ACTIVO (Dentro de horario)
                
                # Se envía el mensaje de análisis
                send(f"🧠 Analizando EUR/USD y XAU/USD... {datetime.now(mx)}")

                for asset in SYMBOLS:
                    v5 = obtener_velas(asset, 5)
                    v1 = obtener_velas(asset, 1)

                    # Aseguramos tener suficientes velas para indicadores
                    if not v5 or not v1 or len(v5) < 50 or len(v1) < 15: 
                        continue

                    fase, direction = detectar_fase(v5, v1)

                    precio_actual = v1[-1][3]

                    if fase == "PRE" and not prealertas.get(asset):
                        send(f"🟡 <b>PRE-ALERTA</b>\n{asset} | {direction}\nEsperando confirmación...")
                        prealertas[asset] = direction

                    if fase == "ENTRADA":
                        ejecutar_trade(asset, direction, precio_actual) 
                        prealertas[asset] = None

                # Analiza cada 2 minutos (120 segundos)
                time.sleep(120) 

            else:
                # 🔕 MODO SILENCIO TOTAL (Fuera de horario)
                # Duerme 1 hora (3600 segundos) para ahorrar recursos de Render.
                time.sleep(3600) 

        except Exception as e:
            if sesion_activa():
                send(f"⚠️ Error crítico: {e}")
            
            # 🚨 LÓGICA DE REINICIO POR DESCONEXIÓN (SOLUCIÓN AL ERROR DE CONEXIÓN CERRADA)
            if "closed" in str(e) or "reset" in str(e) or "EOF" in str(e):
                send("🔴 Error de Conexión Crítico: REINICIO AUTOMÁTICO ACTIVADO")
                time.sleep(3)
                os._exit(1) # Forzar el reinicio completo de Render
                
            time.sleep(30) # Espera 30 segundos antes del siguiente intento si no fue un error fatal


# ================================
# ▶ IN
