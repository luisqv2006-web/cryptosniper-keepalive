# =============================================================
# CRYPTOSNIPER FX — v25.0 (EUR/USD - MEJORAS COMPLETAS)
# =============================================================
from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
import math
from datetime import datetime, timedelta
import os
import sys

from risk_manager import RiskManager
from deriv_api import DerivAPI 
from firebase_cache import actualizar_estado, guardar_macro
from news_filter import NewsFilter

print("--- SISTEMA v25.0 (EUR/USD) INICIADO ---")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

MONTO_INVERSION = 2.0

SYMBOLS = { "EUR/USD": "EUR/USD" }
DERIV_MAP = { "EUR/USD": "frxEURUSD" }

# Gestión de riesgo: máximo 3 pérdidas diarias ($6), cooldown de 30 min tras 2 pérdidas seguidas
risk = RiskManager(balance_inicial=50.00, max_losses_day=3, max_trades_day=15,
                   timezone="America/Mexico_City", cooldown_minutos=30)

# Inicializar filtro de noticias (si la API key está disponible)
news_filter = None
if FINNHUB_API_KEY:
    news_filter = NewsFilter(FINNHUB_API_KEY)
else:
    print("⚠️ FINNHUB_API_KEY no configurada. Filtro de noticias desactivado.")

# Variables de control para notificaciones de bloqueo
ultimo_estado_bloqueo = False
notificado_bloqueo = False

def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

def sesion_activa():
    ahora = datetime.now(mx)
    h = ahora.hour
    # Filtro de fin de semana (0=lunes, 4=viernes)
    if ahora.weekday() > 4:
        return False
    # Londres + NY: de 6 AM a 3 PM CDMX
    return (6 <= h <= 15)

def on_trade_result(result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS confirmado</b>")
        risk.registrar_perdida()
    from stats import registrar_operacion
    registrar_operacion("AUTO", 1, result)

def obtener_velas(asset, resol):
    global api
    simbolo_deriv = DERIV_MAP.get(asset)
    if not simbolo_deriv: return None
    try:
        velas_data = api.get_candles(simbolo_deriv, resol, count=100)
        if not velas_data or not isinstance(velas_data, list):
            return None
        lista_procesada = []
        for v in velas_data:
            lista_procesada.append((
                float(v['open']), float(v['high']),
                float(v['low']), float(v['close']), 0
            ))
        return lista_procesada
    except Exception as e:
        print(f"Error descargando velas {asset}: {e}")
        return None

# ================================
# INDICADORES TÉCNICOS
# ================================
def calcular_ema(candles, period):
    if len(candles) < period: return None
    cierre = [c[3] for c in candles]
    k = 2 / (period + 1)
    ema = sum(cierre[:period]) / period
    for price in cierre[period:]:
        ema = (price * k) + (ema * (1 - k))
    return ema

def calcular_bollinger(candles, period=20, mult=2):
    if len(candles) < period: return None, None, None
    cierres = [c[3] for c in candles[-period:]]
    sma = sum(cierres) / period
    variance = sum([((x - sma) ** 2) for x in cierres]) / period
    std_dev = math.sqrt(variance)
    return sma + (mult * std_dev), sma, sma - (mult * std_dev)

def calcular_adx(candles, period=14):
    if len(candles) < period*2: return None, None, None
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
        dx_list, di_pos_list, di_neg_list = [], [], []
        for i in range(period, len(atr)):
            smooth_atr = (smooth_atr * (period-1) + atr[i]) / period
            smooth_pos = (smooth_pos * (period-1) + dm_pos[i]) / period
            smooth_neg = (smooth_neg * (period-1) + dm_neg[i]) / period
            di_pos = 100 * (smooth_pos / smooth_atr) if smooth_atr != 0 else 0
            di_neg = 100 * (smooth_neg / smooth_atr) if smooth_atr != 0 else 0
            dx = 100 * abs(di_pos - di_neg) / (di_pos + di_neg) if (di_pos + di_neg) != 0 else 0
            dx_list.append(dx)
            di_pos_list.append(di_pos)
            di_neg_list.append(di_neg)
        if len(dx_list) < period: return None, None, None
        adx = sum(dx_list[:period])/period
        for i in range(period, len(dx_list)):
            adx = (adx * (period-1) + dx_list[i]) / period
        return adx, di_pos_list[-1], di_neg_list[-1]
    except: return None, None, None

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
    return k_values[-1], sum(k_values[-d_period:]) / d_period

def calcular_atr(candles, period=14):
    if len(candles) < period+1: return None
    trs = []
    for i in range(1, len(candles)):
        h, l, c_prev = candles[i][1], candles[i][2], candles[i-1][3]
        tr = max(h-l, abs(h-c_prev), abs(l-c_prev))
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period-1) + trs[i]) / period
    return atr

def verificar_soporte_resistencia(candles, direction, current_price):
    recent = candles[-51:-1]  # excluye la última y penúltima
    if not recent:
        return True
    if direction == "BUY":
        resistance = max([c[1] for c in recent])
        return (resistance - current_price) > 0.0002  # al menos 2 pips
    else:
        support = min([c[2] for c in recent])
        return (current_price - support) > 0.0002

def vela_tiene_cuerpo(vela_data):
    open_p, high_p, low_p, close_p = vela_data[0], vela_data[1], vela_data[2], vela_data[3]
    total_size = high_p - low_p
    body_size = abs(close_p - open_p)
    if total_size == 0: return False
    return (body_size / total_size) > 0.30

# ================================
# LÓGICA DE ENTRADA (AHORA DEVUELVE RAZONES)
# ================================
def detectar_fase(asset, v5, v1, v15, v60):
    razones = []
    ema50_5m = calcular_ema(v5, 50)
    ema200_60m = calcular_ema(v60, 200) if v60 and len(v60) > 200 else None
    upper_bb, mid_bb, lower_bb = calcular_bollinger(v5, 20, 2)
    adx, di_plus, di_minus = calcular_adx(v5, 14)
    stoch_k, stoch_d = calcular_stoch(v5, 14, 3)
    atr = calcular_atr(v5, 14)

    if not ema50_5m or not adx or not stoch_k or not atr:
        return "NADA", None, False, []

    # Filtro de volatilidad mínima
    if atr < 0.0004:
        return "NADA", None, False, []

    # Tendencia de fondo (EMA200 en 1h)
    tendencia_alcista = True
    tendencia_bajista = True
    if ema200_60m:
        if v5[-2][3] < ema200_60m:
            tendencia_alcista = False
        elif v5[-2][3] > ema200_60m:
            tendencia_bajista = False

    c5_close = v5[-2][3]
    c15_close = v15[-2][3] if v15 else None
    modo_turbo = adx > 30

    # Condiciones de compra
    if c5_close > ema50_5m and tendencia_alcista:
        if not modo_turbo and c15_close is not None and c15_close <= calcular_ema(v15, 50):
            return "NADA", None, False, []
        if adx < 25 or di_plus <= di_minus:
            return "NADA", None, False, []
        if c5_close > mid_bb and stoch_k < 30 and stoch_k > stoch_d:
            if verificar_soporte_resistencia(v5, "BUY", c5_close):
                if vela_tiene_cuerpo(v1[-2]):
                    razones.append(f"ADX {adx:.1f} > 25 y DI+ > DI-")
                    razones.append("Precio sobre EMA50 (5m)")
                    razones.append("Precio > Banda Media Bollinger")
                    razones.append(f"Estocástico K ({stoch_k:.1f}) < 30 y K > D")
                    razones.append("Soporte/Resistencia libre")
                    razones.append("Vela de 1m con cuerpo >30%")
                    if modo_turbo:
                        razones.append("Modo TURBO (ADX > 30)")
                    else:
                        razones.append("Confirmación EMA50 en 15m")
                    return "ENTRADA", "BUY", modo_turbo, razones

    # Condiciones de venta
    elif c5_close < ema50_5m and tendencia_bajista:
        if not modo_turbo and c15_close is not None and c15_close >= calcular_ema(v15, 50):
            return "NADA", None, False, []
        if adx < 25 or di_plus >= di_minus:
            return "NADA", None, False, []
        if c5_close < mid_bb and stoch_k > 70 and stoch_k < stoch_d:
            if verificar_soporte_resistencia(v5, "SELL", c5_close):
                if vela_tiene_cuerpo(v1[-2]):
                    razones.append(f"ADX {adx:.1f} > 25 y DI- > DI+")
                    razones.append("Precio bajo EMA50 (5m)")
                    razones.append("Precio < Banda Media Bollinger")
                    razones.append(f"Estocástico K ({stoch_k:.1f}) > 70 y K < D")
                    razones.append("Soporte/Resistencia libre")
                    razones.append("Vela de 1m con cuerpo >30%")
                    if modo_turbo:
                        razones.append("Modo TURBO (ADX > 30)")
                    else:
                        razones.append("Confirmación EMA50 en 15m")
                    return "ENTRADA", "SELL", modo_turbo, razones

    return "NADA", None, False, []

def ejecutar_trade(asset, direction, price, es_turbo, razones):
    global api
    if not risk.puede_operar():
        print("⛔ Risk Manager bloqueó la operación.")
        return
    simbolo_deriv = DERIV_MAP[asset]
    DURACION_MINUTOS = 5
    tipo_entrada = "🔥 TURBO" if es_turbo else "🛡️ NORMAL"
    
    # Construir mensaje detallado con confluencias
    msg = f"⚡ <b>SEÑAL EUR/USD ({tipo_entrada})</b>\nDir: {direction}\n"
    if razones:
        msg += f"<b>Confluencias detectadas ({len(razones)}):</b>\n"
        for r in razones:
            msg += f"  • {r}\n"
    else:
        msg += "ADX > 25 Confirmado\n"
    
    send(msg)
    
    try:
        contract_id = api.buy(simbolo_deriv, direction, amount=MONTO_INVERSION, duration=DURACION_MINUTOS)
        risk.registrar_trade()
        guardar_macro({"activo": asset, "direccion": direction, "precio": price, "hora": str(datetime.now(mx))})
        send(f"🔵 <b>ORDEN EJECUTADA: {contract_id}</b>\n{direction} | ${MONTO_INVERSION}")
    except Exception as e:
        send(f"❌ <b>ERROR AL COMPRAR:</b> {e}")

def enviar_resumen_diario():
    ganancias = risk.wins_hoy * 1.70
    perdidas = risk.perdidas_hoy * 2.0
    neto = ganancias - perdidas
    msg = (
        "📊 <b>RESUMEN DEL DÍA</b>\n"
        f"✅ Victorias: {risk.wins_hoy}\n"
        f"❌ Derrotas: {risk.perdidas_hoy}\n"
        f"💰 Ganancia bruta: +${ganancias:.2f}\n"
        f"💸 Pérdida bruta: -${perdidas:.2f}\n"
        f"📈 Neto: ${neto:+.2f}\n"
        f"🧾 Operaciones totales: {risk.trades_hoy}\n"
        f"⛔ Límite de pérdidas diarias: {risk.max_losses_day}"
    )
    send(msg)

def analizar():
    global notificado_inicio_dia, notificado_bloqueo
    notificado_inicio_dia = False
    notificado_bloqueo = False
    print("Iniciando Loop de Análisis (EUR/USD)...")
    
    sesion_anterior = False
    
    while True:
        try:
            # --- FILTRO DE NOTICIAS ---
            bloqueado = news_filter and not news_filter.is_safe_to_trade()
            if bloqueado:
                if not notificado_bloqueo:
                    send("🔕 <b>Mercado bloqueado por evento de alto impacto</b> (USD). Se reanudará tras el evento.")
                    notificado_bloqueo = True
                print("🔕 Bloqueado por evento de alto impacto. Esperando...")
                time.sleep(60)
                continue
            else:
                if notificado_bloqueo:
                    send("🔔 <b>Mercado desbloqueado</b>. Reanudando análisis.")
                notificado_bloqueo = False

            sesion_activa_ahora = sesion_activa()
            
            # Detectar transición a fin de sesión para enviar resumen
            if sesion_anterior and not sesion_activa_ahora and risk.trades_hoy > 0:
                enviar_resumen_diario()
            
            sesion_anterior = sesion_activa_ahora

            if sesion_activa_ahora:
                if not notificado_inicio_dia:
                    send("🇪🇺🇺🇸 <b>Bot Activado: EUR/USD</b>\nHorario: 06:00 - 15:00 CDMX (L-V)")
                    notificado_inicio_dia = True

                for asset in SYMBOLS:
                    v5 = obtener_velas(asset, 5)
                    v1 = obtener_velas(asset, 1)
                    v15 = obtener_velas(asset, 15)
                    v60 = obtener_velas(asset, 60)
                    
                    if not v5 or not v1 or not v15:
                        print(f"⚠️ {asset} sin datos.")
                        continue
                    
                    fase, direction, es_turbo, razones = detectar_fase(asset, v5, v1, v15, v60)
                    if fase == "ENTRADA":
                        ejecutar_trade(asset, direction, v1[-2][3], es_turbo, razones)
                        time.sleep(5)
                
                seg = datetime.now().second
                time.sleep(61 - seg)
            else:
                if notificado_inicio_dia:
                    notificado_inicio_dia = False
                    print("Fuera de horario. Durmiendo...")
                time.sleep(600)
        except Exception as e:
            print(f"❌ Error en loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        api = DerivAPI(DERIV_TOKEN, on_trade_result)
        threading.Thread(target=analizar, daemon=True).start()
        while True: time.sleep(10)
    except Exception as e:
        print(f"Error fatal inicio: {e}")
        os._exit(1)
