# =============================================================
# CRYPTOSNIPER FX — v22.0 (MODO NOTICIAS + REBOTE)
# =============================================================
from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
import math
from datetime import datetime
import os
import sys

from auto_copy import AutoCopy
from stats import registrar_operacion
from risk_manager import RiskManager
from deriv_api import DerivAPI 
from firebase_cache import actualizar_estado, guardar_macro

# --- CONFIGURACIÓN ---
print("--- SISTEMA v22.0: FILTRO DE NOTICIAS ACTIVO ---")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

# DINERO Y ACTIVOS
MONTO_INVERSION = 2.0 
SYMBOLS = { "XAU/USD": "XAU/USD" }
DERIV_MAP = { "XAU/USD": "frxXAUUSD" }

# Gestión de Riesgo
risk = RiskManager(balance_inicial=50.00, max_loss_day=6, max_trades_day=15, timezone="America/Mexico_City")

# ==========================================
# 📰 FILTRO DE NOTICIAS (HORA MÉXICO)
# ==========================================
def es_hora_noticia():
    ahora = datetime.now(mx)
    hora_actual = ahora.strftime("%H:%M")
    
    # Lista de "Zonas de Muerte" para XAU/USD
    # Formato: (Inicio, Fin)
    zonas_prohibidas = [
        ("06:25", "06:40"), # Noticias tempranas
        ("07:20", "07:45"), # ⚠️ EL REY: NFP, CPI, PPI (Peligro Extremo)
        ("07:55", "08:10"), # Apertura Wall Street (Volatilidad)
        ("08:50", "09:15"), # ISM / Confianza Consumidor
        ("11:50", "12:10"), # Eventual FED / FOMC
        ("12:50", "13:10")  # Cierres o noticias tarde
    ]

    for inicio, fin in zonas_prohibidas:
        if inicio <= hora_actual <= fin:
            return True, f"{inicio}-{fin}"
            
    return False, None

# ==========================================
# FUNCIONES BÁSICAS
# ==========================================
def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

def sesion_activa():
    h = datetime.now(mx).hour
    # Operamos de 2 AM a 2 PM, pero el filtro de noticias bloqueará las horas malas dentro de esto
    return (2 <= h <= 14) 

def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS confirmado</b>")
        risk.registrar_perdida()
    registrar_operacion("AUTO", 1, result)

def obtener_velas(asset, resol):
    global api
    simbolo_deriv = DERIV_MAP.get(asset)
    if not simbolo_deriv: return None
    try:
        velas_data = api.get_candles(simbolo_deriv, resol, count=70)
        if not velas_data: return None
        lista = []
        for v in velas_data:
            lista.append((float(v['open']), float(v['high']), float(v['low']), float(v['close']), 0))
        return lista
    except: return None

# ==========================================
# 📐 INDICADORES Y ESTRATEGIA
# ==========================================
def calcular_bollinger(candles, period=20, mult=2.5): # Desviación 2.5 para Oro
    if len(candles) < period: return None, None, None
    cierres = [c[3] for c in candles[-period:]]
    sma = sum(cierres) / period
    variance = sum([((x - sma) ** 2) for x in cierres]) / period
    std_dev = math.sqrt(variance)
    return sma + (mult * std_dev), sma, sma - (mult * std_dev)

def calcular_rsi(candles, period=14):
    if len(candles) < period + 1: return None
    changes = [candles[i][3] - candles[i-1][3] for i in range(1, len(candles))]
    gains = [max(0, c) for c in changes]
    losses = [max(0, -c) for c in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def detectar_fase(asset, v5, v1):
    upper, mid, lower = calcular_bollinger(v5, 20, 2.5) 
    rsi = calcular_rsi(v5, 14)
    
    if not upper or not rsi: return "NADA", None, False

    precio_cierre = v5[-2][3] # Vela cerrada anterior
    
    # Log visible en Render
    print(f"📊 {asset} | RSI: {rsi:.1f} | Precio: {precio_cierre}")

    # ESTRATEGIA DE REBOTE (Mean Reversion)
    # VENTA: Toca techo Y RSI > 70
    if precio_cierre >= upper and rsi > 70:
        if v1[-2][3] < v1[-2][0]: # Vela 1m roja confirmando caída
            return "ENTRADA", "SELL", True

    # COMPRA: Toca piso Y RSI < 30
    elif precio_cierre <= lower and rsi < 30:
        if v1[-2][3] > v1[-2][0]: # Vela 1m verde confirmando subida
            return "ENTRADA", "BUY", True
            
    return "NADA", None, False

def ejecutar_trade(asset, direction, price, es_turbo):
    global api
    if not risk.puede_operar(): 
        print("⛔ Risk Manager bloqueó.")
        return

    simbolo_deriv = DERIV_MAP[asset]
    send(f"⚡ <b>SEÑAL DE REBOTE</b>\nActivo: {asset}\nDir: {direction}\nPrecio Extremo Detectado")
    
    try:
        api.buy(simbolo_deriv, direction, amount=MONTO_INVERSION, duration=5)
        risk.registrar_trade()
        guardar_macro({"activo": asset, "direccion": direction, "precio": price, "hora": str(datetime.now(mx))})
        send(f"🔵 <b>ORDEN ENVIADA</b> ({direction})")
    except Exception as e:
        send(f"❌ Error: {e}")

# ==========================================
# 🔄 BUCLE PRINCIPAL
# ==========================================
def analizar():
    notificado_noticia = False
    
    print("Iniciando vigilancia...")
    while True:
        try:
            if sesion_activa():
                # 1. CHEQUEO DE NOTICIAS
                hay_noticia, horario = es_hora_noticia()
                
                if hay_noticia:
                    if not notificado_noticia:
                        send(f"⚠️ <b>ALERTA DE NOTICIAS ({horario})</b>\nBot pausado por seguridad. Alta volatilidad esperada.")
                        notificado_noticia = True
                        print(f"PAUSA: Noticia detectada en rango {horario}")
                    
                    time.sleep(60) # Esperar 1 minuto y volver a checar
                    continue # Saltar análisis
                
                # Si ya pasó la noticia, reseteamos la notificación
                if not hay_noticia and notificado_noticia:
                    send("✅ <b>Mercado estabilizado</b>\nReanudando operaciones.")
                    notificado_noticia = False

                # 2. ANÁLISIS TÉCNICO
                for asset in SYMBOLS:
                    v5 = obtener_velas(asset, 5)
                    v1 = obtener_velas(asset, 1)
                    if not v5 or not v1: continue
                    
                    fase, direction, es_turbo = detectar_fase(asset, v5, v1)
                    
                    if fase == "ENTRADA":
                        ejecutar_trade(asset, direction, v1[-2][3], es_turbo)
                
                # Sincronización
                segundos_restantes = 60 - datetime.now().second
                time.sleep(segundos_restantes + 1)
                
            else:
                time.sleep(600)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        api = DerivAPI(DERIV_TOKEN, on_trade_result)
        threading.Thread(target=analizar, daemon=True).start()
        while True: time.sleep(10)
    except Exception as e:
        print(f"Fatal: {e}")
        os._exit(1)
