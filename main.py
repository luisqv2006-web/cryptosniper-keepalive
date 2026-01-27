# =============================================================
# CRYPTOSNIPER FX — v20.5 (ALARMA DE INICIO + ANTI-BAN)
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

# --- VARIABLES DE CONTROL ---
notificado_inicio_dia = False  # Variable para controlar la alarma diaria

print("--- SISTEMA v20.5 CON ALARMA INICIADO ---")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

# ==========================================
# 💰 DINERO
# ==========================================
MONTO_INVERSION = 2.0 

SYMBOLS = { "XAU/USD": "XAU/USD" }
DERIV_MAP = { "XAU/USD": "frxXAUUSD" }

risk = RiskManager(balance_inicial=41.64, max_loss_day=6, max_trades_day=15, timezone="America/Mexico_City")

def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

def sesion_activa():
    h = datetime.now(mx).hour
    # Horario operativo: 2 AM a 12 PM (Mediodía)
    return (2 <= h <= 12) 

def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS confirmado</b>")
        risk.registrar_perdida()
    registrar_operacion("AUTO", 1, result)

def obtener_velas(asset, resol):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOLS[asset]}&interval={resol}min&exchange=FOREX&outputsize=70&apikey={TWELVE_API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if "values" not in r: return None
        data = r["values"]
        data.reverse()
        return [(float(v["open"]), float(v["high"]), float(v["low"]), float(v["close"]), float(v.get("volume", 1))) for v in data]
    except: return None

# ================================
# 📐 INDICADORES TÉCNICOS
# ================================
def calcular_ema(candles, period):
    if len(candles) < period: return None
    cierre = [c[3] for c in candles]
    k = 2 / (period + 1)
    ema = sum(cierre[:period]) / period
    for price in cierre[period:]: ema = (price * k) + (ema * (1 - k))
    return ema

def calcular_bollinger(candles, period=20, mult=2):
    if len(candles) < period: return None, None, None
    cierres = [c[3] for c in candles[-period:]]
    sma = sum(cierres) / period
    variance = sum([((x - sma) ** 2) for x in cierres]) / period
    std_dev = math.sqrt(variance)
    return sma + (mult * std_dev), sma, sma - (mult * std_dev)

def calcular_adx(candles, period=14):
    if len(candles) < period * 2: return None
    try:
        atr, dm_pos, dm_neg = [], [], []
        for i in range(1, len(candles)):
            h, l, c_prev = candles[i][1], candles[i][2], candles[i-1][3]
            tr = max(h-l, abs(h-c_prev), abs(l-c_prev))
            atr.append(tr)
            up = h - candles[i-1][1]
            down = candles[i-1][2] - l
            dm_pos.append(up if up > down and up > 0 else 0)
            dm_neg.append(down if down > up and down > 0 else 0)
        smooth_atr = sum(atr[:period])/period
        smooth_pos = sum(dm_pos[:period])/period
        smooth_neg = sum(dm_neg[:period])/period
        dx_list = []
        for i in range(period, len(atr)):
            smooth_atr = (smooth_atr * (period-1) + atr[i]) / period
            smooth_pos = (smooth_pos * (period-1) + dm_pos[i]) / period
            smooth_neg = (smooth_neg * (period-1) + dm_neg[i]) / period
            di_pos = 100 * (smooth_pos / smooth_atr) if smooth_atr != 0 else 0
            di_neg = 100 * (smooth_neg / smooth_atr) if smooth_atr != 0 else 0
            dx = 100 * abs(di_pos - di_neg) / (di_pos + di_neg) if (di_pos + di_neg) != 0 else 0
            dx_list.append(dx)
        if len(dx_list) < period: return None
        adx = sum(dx_list[:period]) / period
        for i in range(period, len(dx_list)):
            adx = (adx * (period-1) + dx_list[i]) / period
        return adx
    except: return None

def calcular_stoch(candles, k_period=14, d_period=3):
    if len(candles) < k_period + d_period: return None, None
    closes = [c[3] for c in candles]
    lows = [c[2] for c in candles]
    highs = [c[1] for c in candles]
    k_values = []
    for i in range(k_period, len(candles)):
        current_close = closes[i]
        lowest_low = min(lows[i-k_period+1:i+1])
        highest_high = max(highs[i-k_period+1:i+1])
        if highest_high - lowest_low == 0: k = 100
        else: k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        k_values.append(k)
    if len(k_values) < d_period: return None, None
    current_k = k_values[-1]
    current_d = sum(k_values[-d_period:]) / d_period
    return current_k, current_d

def verificar_espacio_sr(candles, direction, current_price):
    lookback = 50 
    recent_candles = candles[-lookback:-1]
    if direction == "BUY":
        resistance = max([c[1] for c in recent_candles])
        avg_body = sum([abs(c[3]-c[0]) for c in recent_candles]) / lookback
        if (resistance - current_price) < (avg_body * 0.5): return False
    elif direction == "SELL":
        support = min([c[2] for c in recent_candles])
        avg_body = sum([abs(c[3]-c[0]) for c in recent_candles]) / lookback
        if (current_price - support) < (avg_body * 0.5): return False
    return True

def vela_tiene_cuerpo(vela_data):
    open_p, high_p, low_p, close_p = vela_data[0], vela_data[1], vela_data[2], vela_data[3]
    total_size = high_p - low_p
    body_size = abs(close_p - open_p)
    if total_size == 0: return False
    return (body_size / total_size) > 0.30

# ================================
# 🧠 LÓGICA V20.5 (ADAPTATIVA)
# ================================
def detectar_fase(v5, v1, v15):
    ema50_5m = calcular_ema(v5, 50)
    upper_bb, mid_bb, lower_bb = calcular_bollinger(v5, 20)
    adx_val = calcular_adx(v5, 14)
    stoch_k, stoch_d = calcular_stoch(v5, 14, 3)
    ema50_15m = calcular_ema(v15, 50)

    if not ema50_5m or not ema50_15m or not stoch_k or not adx_val: return "NADA", None, False

    if adx_val < 20: return "NADA", None, False

    c5_close = v5[-1][3]
    c15_close = v15[-1][3]
    modo_turbo = adx_val > 30
    
    if c5_close > ema50_5m: 
        if modo_turbo or (c15_close > ema50_15m): 
            if c5_close > mid_bb and stoch_k < 80 and stoch_k > stoch_d:
                if verificar_espacio_sr(v5, "BUY", c5_close):
                    if vela_tiene_cuerpo(v1[-1]):
                         return "ENTRADA", "BUY", modo_turbo

    elif c5_close < ema50_5m:
        if modo_turbo or (c15_close < ema50_15m): 
            if c5_close < mid_bb and stoch_k > 20 and stoch_k < stoch_d:
                if verificar_espacio_sr(v5, "SELL", c5_close):
                     if vela_tiene_cuerpo(v1[-1]):
                        return "ENTRADA", "SELL", modo_turbo
            
    return "NADA", None, False

def ejecutar_trade(asset, direction, price, es_turbo):
    global api
    if not risk.puede_operar(): return
    simbolo_deriv = DERIV_MAP[asset]
    DURACION_MINUTOS = 5 
    tipo_entrada = "🔥 MODO TURBO" if es_turbo else "🛡️ MODO SEGURO"
    
    send(f"⚡ <b>SEÑAL ({tipo_entrada})</b>\nDir: {direction}\nInversión: <b>${MONTO_INVERSION}</b>")
    
    try:
        contract_id = api.buy(simbolo_deriv, direction, amount=MONTO_INVERSION, duration=DURACION_MINUTOS)
        risk.registrar_trade()
        guardar_macro({"activo": asset, "direccion": direction, "precio": price, "hora": str(datetime.now(mx))})
        send(f"🔵 <b>ORDEN ACEPTADA: {contract_id}</b>\nTipo: {tipo_entrada}\nDirección: {direction}")
    
    except Exception as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower() or "limit" in error_msg.lower():
            send("⏳ <b>PAUSA DE SEGURIDAD (15 MIN)</b>\nDeriv detectó muchas conexiones. Esperando...")
            time.sleep(900) 
            return

        if "RECHAZADO" in error_msg: send(f"⚠️ <b>DERIV RECHAZÓ:</b> {error_msg}")
        elif "Connection" in error_msg or "Timeout" in error_msg:
            print(f"Reinicio silencioso: {e}")
            os._exit(1)
        else: send(f"❌ <b>ERROR:</b> {e}")

def analizar():
    global notificado_inicio_dia
    print("Bot v20.5 ALARMA Iniciado")
    send(f"✅ <b>BOT v20.5 CON ALARMA ONLINE</b>\nInversión: ${MONTO_INVERSION}\nEsperando a las 2:00 AM...")
    
    while True:
        try:
            if sesion_activa():
                # --- AQUÍ ESTÁ TU ALARMA ---
                if not notificado_inicio_dia:
                    send("⏰ <b>¡DING DONG! Despertador</b>\nIniciando sesión Londres. Estoy buscando oportunidades...")
                    notificado_inicio_dia = True

                for asset in SYMBOLS:
                    v5 = obtener_velas(asset, 5)
                    v1 = obtener_velas(asset, 1)
                    v15 = obtener_velas(asset, 15) 
                    if not v5 or not v1 or not v15: continue
                    fase, direction, es_turbo = detectar_fase(v5, v1, v15)
                    if fase == "ENTRADA":
                        ejecutar_trade(asset, direction, v1[-1][3], es_turbo)
                time.sleep(60)
            else:
                # Si se hace tarde, reseteamos la alarma para mañana
                if notificado_inicio_dia:
                    notificado_inicio_dia = False
                    print("Reiniciando alarma para mañana.")
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
        print(f"Error fatal inicio: {e}")
        os._exit(1)
