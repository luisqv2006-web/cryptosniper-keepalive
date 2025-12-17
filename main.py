# =============================================================
# CRYPTOSNIPER FX — v16.4 VERDAD ABSOLUTA (CORREGIDO)
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

# MAPEO DE ACTIVOS: Corregido para evitar error de validación en Deriv
ASSETS = {
    "EUR/USD": {"twelve": "EUR/USD", "deriv": "frxEURUSD"},
    "XAU/USD": {"twelve": "XAU/USD", "deriv": "frxXAUUSD"}
}

# Ajustado al saldo actual de 27.08 USD visto en captura
risk = RiskManager(
    balance_inicial=27.08, 
    max_loss_day=5, 
    max_trades_day=15, 
    timezone="America/Mexico_City"
)

def send(msg):
    try:
        requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

def sesion_activa():
    h = datetime.now(mx).hour
    return (2 <= h <= 5) or (7 <= h <= 10)

def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado por Servidor</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS confirmado por Servidor</b>")
        risk.registrar_perdida()
    registrar_operacion("AUTO", 1, result)

def obtener_velas(asset_name, resol):
    # Usamos el símbolo para TwelveData (ej. EUR/USD)
    symbol_twelve = ASSETS[asset_name]["twelve"]
    url = f"https://api.twelvedata.com/time_series?symbol={symbol_twelve}&interval={resol}min&exchange=FOREX&outputsize=70&apikey={TWELVE_API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if "values" not in r: return None
        data = r["values"]
        data.reverse()
        return [(float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]), float(v.get("volume", 1))) for v in data]
    except: return None

def calcular_ema(candles, period):
    if len(candles) < period: return None
    cierre = [c[3] for c in candles]
    k = 2 / (period + 1)
    ema = sum(cierre[:period]) / period
    for price in cierre[period:]: ema = (price * k) + (ema * (1 - k))
    return ema

def calcular_rsi(candles, period=14):
    if len(candles) < period + 1: return None
    cierres = [c[3] for c in candles]
    ganancias, perdidas = [], []
    for i in range(1, len(cierres)):
        cambio = cierres[i] - cierres[i-1]
        ganancias.append(max(0, cambio)); perdidas.append(max(0, -cambio))
    avg_gain = sum(ganancias[:period]) / period
    avg_loss = sum(perdidas[:period]) / period
    for i in range(period, len(ganancias)):
        avg_gain = (avg_gain * (period - 1) + ganancias[i]) / period
        avg_loss = (avg_loss * (period - 1) + perdidas[i]) / period
    if avg_loss == 0: return 100.0
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

def detectar_fase(v5, v1):
    ema50 = calcular_ema(v5, 50)
    rsi14 = calcular_rsi(v1, 14)
    if not ema50 or not rsi14: return "NADA", None
    
    c5, c1 = v5[-1][3], v1[-1][3]
    
    if c5 > ema50 and rsi14 < 70:
        if c5 > v5[-2][1] and c1 > v1[-2][3]: return "ENTRADA", "BUY"
    elif c5 < ema50 and rsi14 > 30:
        if c5 < v5[-2][2] and c1 < v1[-2][3]: return "ENTRADA", "SELL"
    return "NADA", None

# ==========================================
# 🚀 EJECUCIÓN SÍNCRONA
# ==========================================
def ejecutar_trade(asset_name, direction, price):
    global api
    if not risk.puede_operar(): return
    
    send(f"⏳ Solicitando {direction} en {asset_name} al servidor...")
    
    # Usamos el símbolo técnico para Deriv (ej. frxXAUUSD)
    deriv_symbol = ASSETS[asset_name]["deriv"]
    
    try:
        # Enviamos la orden con el formato que Deriv acepta
        contract_id = api.buy(deriv_symbol, direction, amount=1, duration=1)
        
        risk.registrar_trade()
        guardar_macro({"activo": asset_name, "direccion": direction, "precio": price, "hora": str(datetime.now(mx))})
        
        send(f"🔵 <b>ORDEN ACEPTADA POR DERIV</b>\nID Contrato: {contract_id}\nActivo: {asset_name}\nDir: {direction}")
        
    except Exception as e:
        error_msg = str(e)
        if "Authorization required" in error_msg:
             send("❌ Error: Token inválido o expirado.")
        elif "Insufficient balance" in error_msg:
             send("❌ Error: Saldo insuficiente.")
        else:
             send(f"❌ <b>DERIV RECHAZÓ LA ORDEN:</b>\n{error_msg}")
        
        if "Connection" in error_msg or "Timeout" in error_msg:
            os._exit(1)

def analizar():
    send("✅ <b>BOT SÍNCRONO V16.4 ONLINE</b>\nEsperando confirmación real de cada trade.")
    while True:
        try:
            if sesion_activa():
                for asset_name in ASSETS:
                    v5, v1 = obtener_velas(asset_name, 5), obtener_velas(asset_name, 1)
                    if not v5 or not v1: continue
                    fase, direction = detectar_fase(v5, v1)
                    if fase == "ENTRADA":
                        ejecutar_trade(asset_name, direction, v1[-1][3])
                time.sleep(60)
            else:
                time.sleep(600)
        except Exception as e:
            print(f"Error loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        api = DerivAPI(DERIV_TOKEN, on_trade_result)
        threading.Thread(target=analizar, daemon=True).start()
        while True: time.sleep(10)
    except Exception as e:
        send(f"❌ Error Inicio: {e}")
        os._exit(1)
