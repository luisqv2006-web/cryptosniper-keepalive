# =============================================================
# CRYPTOSNIPER FX — v16.4 PRO (AUTO-RECONNECT) - ACTUALIZADO
# =============================================================
from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
from datetime import datetime
import os
import sys

from auto_copy import AutoCopy
from stats import registrar_operacion
from risk_manager import RiskManager
from deriv_api import DerivAPI 
from firebase_cache import actualizar_estado, guardar_macro

# ================================
# 🔐 CONFIGURACIÓN
# ================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

# Símbolos definitivos para Deriv Financial
ASSETS = {
    "EUR/USD": {"twelve": "EUR/USD", "deriv": "frxEURUSD"},
    "XAU/USD": {"twelve": "XAU/USD", "deriv": "frxXAUUSD"}
}

risk = RiskManager(
    balance_inicial=27.08, 
    max_loss_day=5, 
    max_trades_day=15, 
    timezone="America/Mexico_City"
)

def send(msg):
    try:
        requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=5)
    except: pass

def on_trade_result(result):
    msg = "✅ <b>WIN confirmado</b>" if result == "WIN" else "❌ <b>LOSS confirmado</b>"
    send(msg)
    if result == "WIN": risk.registrar_win()
    else: risk.registrar_perdida()
    registrar_operacion("AUTO", 1, result)

# ==========================================
# 🔄 GESTIÓN DE CONEXIÓN (OPCIÓN DEFINITIVA)
# ==========================================
def conectar_api():
    global api
    try:
        api = DerivAPI(DERIV_TOKEN, on_trade_result)
        return True
    except Exception as e:
        print(f"Error de conexión: {e}")
        return False

def ejecutar_trade(asset_name, direction, price):
    global api
    if not risk.puede_operar(): return
    
    deriv_symbol = ASSETS[asset_name]["deriv"]
    send(f"⏳ Enviando {direction} en {asset_name}...")
    
    try:
        # ===========================================================
        # CAMBIO DEFINITIVO: Duración aumentada a 5 minutos y contrato
        # para evitar el error "Trading is not offered for this duration"
        # ===========================================================
        contract_id = api.buy(
            symbol=deriv_symbol, 
            direction=direction, 
            amount=1, 
            duration=5,         # Se cambió de 1 a 5
            duration_unit='m'   # Se especifica 'm' para minutos
        )
        # ===========================================================
        
        risk.registrar_trade()
        guardar_macro({"activo": asset_name, "direccion": direction, "precio": price, "hora": str(datetime.now(mx))})
        send(f"🔵 <b>ORDEN EXITOSA</b>\nID: {contract_id}\nActivo: {asset_name}")
        
    except Exception as e:
        error_msg = str(e)
        send(f"⚠️ <b>FALLO: RECHAZADO POR DERIV:</b> {error_msg}")
        
        # Manejo de reconexión si el servidor de Render falla (E/S)
        if "closed" in error_msg.lower() or "connection" in error_msg.lower() or "tiempo de espera" in error_msg.lower():
            send("🔄 Error de servidor detectado. Reiniciando instancia en Render...")
            os.execv(sys.executable, ['python'] + sys.argv)

def obtener_velas(asset_name, resol):
    symbol = ASSETS[asset_name]["twelve"]
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={resol}min&outputsize=70&apikey={TWELVE_API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if "values" not in r: return None
        data = r["values"]
        data.reverse()
        return [(float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"])) for v in data]
    except: return None

def analizar():
    send("🚀 <b>SISTEMA REINICIADO Y ONLINE</b>")
    while True:
        try:
            h = datetime.now(mx).hour
            # Horarios de operación ajustados
            if (2 <= h <= 5) or (7 <= h <= 10):
                for asset in ASSETS:
                    v5, v1 = obtener_velas(asset, 5), obtener_velas(asset, 1)
                    if not v5 or not v1: continue
                    
                    c5, ema50 = v5[-1][3], sum([x[3] for x in v5[-50:]])/50
                    if c5 > ema50: direction = "BUY"
                    elif c5 < ema50: direction = "SELL"
                    else: continue
                    
                    ejecutar_trade(asset, direction, v1[-1][3])
                time.sleep(60)
            else:
                # Tiempo de espera fuera de horario
                time.sleep(300)
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    if conectar_api():
        analizar()
    else:
        send("❌ Error fatal de inicio en Render. Revisa tokens.")
