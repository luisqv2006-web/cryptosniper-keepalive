# =============================================================
# CRYPTOSNIPER FX — v16.3 TOTAL LOCKDOWN (EDICIÓN DEFINITIVA)
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
SYMBOLS = {"EUR/USD": "EUR/USD", "XAU/USD": "XAU/USD"}

# ================================
# 📌 RISK MANAGER (Ajustado a saldo real de $27.08)
# ================================
risk = RiskManager(
    balance_inicial=27.08, 
    max_loss_day=5, 
    max_trades_day=15, 
    timezone="America/Mexico_City"
)

# ================================
# 📩 TELEGRAM
# ================================
def send(msg):
    try:
        requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: 
        pass

# ================================
# ⏰ SESIONES (HORA MÉXICO)
# ================================
def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 5) or (7 <= h <= 10)

# ================================
# 📊 RESULTADOS DERIV
# ================================
def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado en el servidor</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS confirmado en el servidor</b>")
        risk.registrar_perdida()
    registrar_operacion("AUTO", 1, result)

# ================================
# 📊 OBTENER VELAS (TwelveData)
# ================================
def obtener_velas(asset, resol):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOLS[asset]}&interval={resol}min&exchange=FOREX&outputsize=70&apikey={TWELVE_API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if "values" not in r: return None
        data = r["values"]
        data.reverse()
        return [(float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]), float(v.get("volume", 1))) for v in data]
    except: 
        return None

# ================================
# 📐 INDICADORES TÉCNICOS
# ================================
def calcular_ema(candles, period):
    if len(candles) < period: return None
    cierre = [c[3] for c in candles]
    k = 2 / (period + 1)
    ema = sum(cierre[:period]) / period
    for price in cierre[period:]: 
        ema = (price * k) + (ema * (1 - k))
    return ema

def calcular_rsi(candles, period=14):
    if len(candles) < period + 1: return None
    cierres = [c[3] for c in candles]
    ganancias, perdidas = [], []
    for i in range(1, len(cierres)):
        cambio = cierres[i] - cierres[i-1]
        ganancias.append(max(0, cambio))
        perdidas.append(max(0, -cambio))
    avg_gain = sum(ganancias[:period]) / period
    avg_loss = sum(perdidas[:period]) / period
    for i in range(period, len(ganancias)):
        avg_gain = (avg_gain * (period - 1) + ganancias[i]) / period
        avg_loss = (avg_loss * (period - 1) + perdidas[i]) / period
    if avg_loss == 0: return 100.0
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

# ================================
# 🔍 LÓGICA DE ENTRADA
# ================================
def detectar_fase(v5, v1):
    ema50 = calcular_ema(v5, 50)
    rsi14 = calcular_rsi(v1, 14)
    if not ema50 or not rsi14: return "NADA", None
    
    c5, c1 = v5[-1][3], v1[-1][3]
    
    # ESTRATEGIA: Cruce de EMA + RSI + Confirmación de Vela
    if c5 > ema50 and rsi14 < 70:
        if c5 > v5[-2][1] and c1 > v1[-2][3]: 
            return "ENTRADA", "BUY"
    elif c5 < ema50 and rsi14 > 30:
        if c5 < v5[-2][2] and c1 < v1[-2][3]: 
            return "ENTRADA", "SELL"
    return "NADA", None

# ================================
# 🚀 EJECUTAR TRADE (Blindado)
# ================================
def ejecutar_trade(asset, direction, price):
    global api
    if not risk.puede_operar(): 
        send("🛑 Pausa por gestión de riesgo.")
        return
    
    send(f"⏳ Procesando {direction} en {asset}...")
    try:
        # Envío físico a la API de Deriv
        api.buy(SYMBOLS[asset], direction, amount=1, duration=1)
        
        # Registro local
        risk.registrar_trade()
        guardar_macro({"activo": asset, "direccion": direction, "precio": price, "hora": str(datetime.now(mx))})
        
        send(f"🔴 <b>ORDEN ENVIADA EXITOSAMENTE</b>\nActivo: {asset}\nOperación: {direction}\nSaldo objetivo: $27.08")
    except Exception as e:
        send(f"❌ <b>ERROR DE EJECUCIÓN:</b> {e}\nRevisando conexión...")
        os._exit(1) # Forzar reinicio para limpiar el WebSocket

# ================================
# 🔄 LOOP DE ANÁLISIS
# ================================
def analizar():
    send("✅ <b>BOT SNIPER v16.3 ONLINE</b>\nMonitoreando EUR/USD y XAU/USD")
    while True:
        try:
            if sesion_activa():
                for asset in SYMBOLS:
                    v5, v1 = obtener_velas(asset, 5), obtener_velas(asset, 1)
                    if not v5 or not v1: continue
                    
                    fase, direction = detectar_fase(v5, v1)
                    if fase == "ENTRADA":
                        ejecutar_trade(asset, direction, v1[-1][3])
                time.sleep(60) # Análisis cada minuto
            else:
                time.sleep(600) # Dormir 10 min fuera de horario
        except Exception as e:
            print(f"Error en loop: {e}")
            time.sleep(10)

# ================================
# ▶ INICIO DEL SISTEMA
# ================================
if __name__ == "__main__":
    try:
        # Inicialización con la nueva clase DerivAPI
        api = DerivAPI(DERIV_TOKEN, on_trade_result)
        
        # Lanzar hilo de análisis
        hilo_bot = threading.Thread(target=analizar, daemon=True)
        hilo_bot.start()
        
        # Mantener el script vivo
        while True: 
            time.sleep(10)
    except Exception as e:
        send(f"❌ Error fatal al iniciar: {e}")
        os._exit(1)
