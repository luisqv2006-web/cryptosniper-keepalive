# =============================================================
# CRYPTOSNIPER FX — v25.2 (EUR/USD - INTERACTIVO + CSV + SALDO + HOLIDAY)
# =============================================================
from keep_alive import keep_alive
keep_alive()

import time
import requests
import threading
import pytz
import math
import csv
import os
import sys
from datetime import datetime, timedelta

from risk_manager import RiskManager
from deriv_api import DerivAPI 
from firebase_cache import actualizar_estado, guardar_macro
from news_filter import NewsFilter
import holidays

print("--- SISTEMA v25.2 (EUR/USD) INICIADO ---")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DERIV_TOKEN = os.getenv("DERIV_TOKEN")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

API = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
mx = pytz.timezone("America/Mexico_City")

MONTO_INVERSION = 2.0
BALANCE_MINIMO = 10.0   # mínimo para operar

SYMBOLS = { "EUR/USD": "EUR/USD" }
DERIV_MAP = { "EUR/USD": "frxEURUSD" }

# Gestión de riesgo (max 3 pérdidas, profit target $6, cooldown 30 min)
risk = RiskManager(balance_inicial=50.00, max_losses_day=3, max_profit_day=3.0,
                   max_trades_day=15, timezone="America/Mexico_City", cooldown_minutos=30)

# Filtro de noticias (USD + EUR)
news_filter = None
if FINNHUB_API_KEY:
    news_filter = NewsFilter(FINNHUB_API_KEY)
else:
    print("⚠️ FINNHUB_API_KEY no configurada. Filtro de noticias desactivado.")

# Variables globales para comandos y estado
bot_paused = False           # pausa manual
stop_for_day = False         # detener el día completo
last_signal_time = None      # para alarma de inactividad
inactivity_alerted = False   # si ya se envió el aviso
trade_log_pending = {}       # {contract_id: (direction, amount, timestamp, razones_str)}
trade_allowed_today = True   # se actualiza al inicio del día (feriados)
balance = None               # saldo real de Deriv

# --- Función para enviar mensajes a Telegram ---
def send(msg):
    if not TOKEN or not CHAT_ID: return
    try: requests.post(API, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except: pass

# --- Hilo de escucha de comandos de Telegram (long polling) ---
def telegram_polling():
    global bot_paused, stop_for_day
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            resp = requests.get(url, params=params, timeout=35)
            data = resp.json()
            if data.get("ok"):
                for upd in data["result"]:
                    offset = upd["update_id"] + 1
                    msg_obj = upd.get("message")
                    if not msg_obj: continue
                    text = msg_obj.get("text", "").strip().lower()
                    if not text.startswith("/"): continue
                    
                    if text == "/status":
                        # Calcular estadísticas actuales
                        g = risk.wins_hoy * 1.70
                        p = risk.perdidas_hoy * 2.0
                        neto = g - p
                        estado = "ACTIVO"
                        if stop_for_day:
                            estado = "DETENIDO (fin de día)"
                        elif bot_paused:
                            estado = "PAUSADO"
                        elif not risk.puede_operar():
                            estado = "BLOQUEADO por gestión de riesgo"
                        msg_resp = (
                            "📊 <b>ESTADO DEL BOT</b>\n"
                            f"🔹 Estado: {estado}\n"
                            f"✅ Victorias hoy: {risk.wins_hoy}\n"
                            f"❌ Derrotas hoy: {risk.perdidas_hoy}\n"
                            f"💰 Neto: ${neto:+.2f}\n"
                            f"🧾 Operaciones: {risk.trades_hoy}\n"
                            f"⛔ Límite pérdidas: {risk.max_losses_day}\n"
                            f"🎯 Objetivo ganancia: ${risk.max_profit_day:.2f}"
                        )
                        if balance:
                            msg_resp += f"\n💵 Saldo Deriv: ${balance:.2f}"
                        send(msg_resp)
                    elif text == "/pause":
                        bot_paused = True
                        send("⏸️ <b>Bot PAUSADO</b>. No se abrirán nuevas operaciones hasta que uses /resume.")
                    elif text == "/resume":
                        bot_paused = False
                        send("▶️ <b>Bot REANUDADO</b>. Las operaciones pueden continuar.")
                    elif text == "/stopday":
                        stop_for_day = True
                        bot_paused = False
                        send("🛑 <b>Bot DETENIDO por el día</b>. Mañana se reiniciará automáticamente.")
            time.sleep(1)
        except Exception as e:
            print(f"Error en polling Telegram: {e}")
            time.sleep(10)

# --- Registro CSV ---
def init_csv_if_needed():
    today_str = datetime.now(mx).strftime("%Y-%m-%d")
    filename = f"trades_{today_str}.csv"
    if not os.path.exists(filename):
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Hora", "Direccion", "Monto", "Resultado", "Confluencias"])

def log_trade_csv(hora, direction, amount, result, razones_str):
    today_str = datetime.now(mx).strftime("%Y-%m-%d")
    filename = f"trades_{today_str}.csv"
    try:
        with open(filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([hora, direction, amount, result, razones_str])
    except Exception as e:
        print(f"Error escribiendo CSV: {e}")

# --- Filtro de día post‑feriado ---
def ayer_fue_feriado():
    """Devuelve True si ayer fue feriado en EE.UU. o en los principales países de la Eurozona."""
    ayer = datetime.now(mx).date() - timedelta(days=1)
    # Feriados EE.UU.
    us_holidays = holidays.UnitedStates(years=ayer.year)
    if ayer in us_holidays:
        return True
    # Principales países Eurozona (feriados nacionales)
    for country_code in ["DE", "FR", "IT", "ES"]:  # Alemania, Francia, Italia, España
        try:
            eu_holidays = holidays.country_holidays(country_code, years=ayer.year)
            if ayer in eu_holidays:
                return True
        except:
            pass
    return False

# --- Verificación de saldo en Deriv ---
def verificar_saldo():
    global api, balance
    try:
        balance = api.get_balance()
        if balance is None:
            send("⚠️ No se pudo obtener el saldo de Deriv. Operaciones permitidas.")
            return True
        if balance < BALANCE_MINIMO:
            send(f"⛔ Saldo bajo (${balance:.2f}) < mínimo (${BALANCE_MINIMO}). Operaciones detenidas.")
            return False
        send(f"💵 Saldo en Deriv: ${balance:.2f}. Listo para operar.")
        return True
    except Exception as e:
        send(f"Error al obtener saldo: {e}")
        return True  # Si falla, permitir para no bloquear sin motivo

# --- Funciones de horario y trading (mantienen lógica original) ---
def sesion_activa():
    ahora = datetime.now(mx)
    h = ahora.hour
    m = ahora.minute
    # Fines de semana
    if ahora.weekday() > 4:
        return False
    # Fuera de franja horaria
    if not (6 <= h <= 15):
        return False
    # Evitar primeros 15 min tras apertura (6:00-6:14)
    if h == 6 and m < 15:
        return False
    # Evitar últimos 15 min antes del cierre (14:45-15:00)
    if h == 14 and m >= 45:
        return False
    return True

def on_trade_result(result):
    # Este callback se ejecuta cuando Deriv informa el resultado del contrato
    # Buscar la entrada pendiente en trade_log_pending
    # (usamos el contract_id que viene en la respuesta, pero aquí no lo tenemos directamente;
    #  necesitamos pasar contract_id al callback. Modificamos deriv_api para que el callback reciba (contract_id, result))
    # Para no cambiar mucho, en lugar de eso, vamos a almacenar la última operación y asumir que llega en orden.
    # Este es un punto débil, lo resolveremos pasando contract_id desde deriv_api.
    # Actualizaremos deriv_api para que on_trade_result reciba contract_id y result.
    pass  # Lo manejaremos modificando deriv_api y esta función en main (ver más abajo)

# La verdadera callback que recibe (contract_id, result)
def trade_result_callback(contract_id, result):
    if result == "WIN":
        send("✅ <b>WIN confirmado</b>")
        risk.registrar_win()
    else:
        send("❌ <b>LOSS confirmado</b>")
        risk.registrar_perdida()
    # Registrar en CSV y limpiar pendientes
    pendiente = trade_log_pending.pop(contract_id, None)
    if pendiente:
        direction, amount, hora, razones_str = pendiente
        log_trade_csv(hora, direction, amount, result, razones_str)
    # Estadísticas (opcional)
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
# INDICADORES TÉCNICOS (sin cambios)
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
    recent = candles[-51:-1]
    if not recent:
        return True
    if direction == "BUY":
        resistance = max([c[1] for c in recent])
        return (resistance - current_price) > 0.0002
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
# LÓGICA DE ENTRADA (igual, devuelve razones y ATR)
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
        return "NADA", None, False, [], None

    if atr < 0.0004:
        return "NADA", None, False, [], None

    # Filtro de rango estrecho (consolidación)
    if len(v5) >= 10:
        recent_10 = v5[-10:]
        rango = max([c[1] for c in recent_10]) - min([c[2] for c in recent_10])
        if rango < 0.0010:
            return "NADA", None, False, [], None

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

    # Compra
    if c5_close > ema50_5m and tendencia_alcista:
        if not modo_turbo and c15_close is not None and c15_close <= calcular_ema(v15, 50):
            return "NADA", None, False, [], None
        if adx < 25 or di_plus <= di_minus:
            return "NADA", None, False, [], None
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
                    return "ENTRADA", "BUY", modo_turbo, razones, atr

    # Venta
    elif c5_close < ema50_5m and tendencia_bajista:
        if not modo_turbo and c15_close is not None and c15_close >= calcular_ema(v15, 50):
            return "NADA", None, False, [], None
        if adx < 25 or di_plus >= di_minus:
            return "NADA", None, False, [], None
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
                    return "ENTRADA", "SELL", modo_turbo, razones, atr

    return "NADA", None, False, [], None

def ejecutar_trade(asset, direction, price, es_turbo, razones, atr):
    global api, last_signal_time, inactivity_alerted
    simbolo_deriv = DERIV_MAP[asset]
    DURACION_MINUTOS = 5
    tipo_entrada = "🔥 TURBO" if es_turbo else "🛡️ NORMAL"
    
    monto = MONTO_INVERSION
    if atr and atr > 0.0010:
        monto = 1.0
    
    msg = f"⚡ <b>SEÑAL EUR/USD ({tipo_entrada})</b>\nDir: {direction}\n"
    if razones:
        msg += f"<b>Confluencias detectadas ({len(razones)}):</b>\n"
        for r in razones:
            msg += f"  • {r}\n"
    if monto != MONTO_INVERSION:
        msg += f"⚠️ Volatilidad alta (ATR>10 pips) → Monto reducido a ${monto}\n"
    
    send(msg)
    
    try:
        contract_id = api.buy(simbolo_deriv, direction, amount=monto, duration=DURACION_MINUTOS)
        risk.registrar_trade()
        ahora = datetime.now(mx)
        hora_str = ahora.strftime("%H:%M")
        razones_str = "; ".join(razones) if razones else ""
        # Guardar pendiente para CSV y resultado
        trade_log_pending[contract_id] = (direction, monto, hora_str, razones_str)
        guardar_macro({"activo": asset, "direccion": direction, "precio": price, "monto": monto, "hora": str(ahora)})
        send(f"🔵 <b>ORDEN EJECUTADA: {contract_id}</b>\n{direction} | ${monto}")
        # Actualizar última señal y resetear alarma
        last_signal_time = time.time()
        inactivity_alerted = False
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
        f"⛔ Límite de pérdidas: {risk.max_losses_day}\n"
        f"🎯 Objetivo de ganancia: ${risk.max_profit_day:.2f}"
    )
    send(msg)

def analizar():
    global notificado_inicio_dia, notificado_bloqueo, bot_paused, stop_for_day
    global last_signal_time, inactivity_alerted, trade_allowed_today, balance
    notificado_inicio_dia = False
    notificado_bloqueo = False
    sesion_anterior = False
    print("Iniciando Loop de Análisis (EUR/USD)...")
    
    while True:
        try:
            # --- Filtro de noticias (USD + EUR) ---
            bloqueado = news_filter and not news_filter.is_safe_to_trade()
            if bloqueado:
                if not notificado_bloqueo:
                    send("🔕 <b>Mercado bloqueado por evento de alto impacto (USD/EUR)</b>. Se reanudará tras el evento.")
                    notificado_bloqueo = True
                time.sleep(60)
                continue
            else:
                if notificado_bloqueo:
                    send("🔔 <b>Mercado desbloqueado</b>. Reanudando análisis.")
                notificado_bloqueo = False

            sesion_activa_ahora = sesion_activa()
            
            # Al inicio de la sesión: verificar día post‑feriado y saldo
            if sesion_activa_ahora and not sesion_anterior:
                # Solo el primer minuto de la sesión
                trade_allowed_today = not ayer_fue_feriado()
                if not trade_allowed_today:
                    send("📅 Ayer fue feriado (EE.UU. / Eurozona). No se opera hoy.")
                else:
                    # Verificar saldo
                    if not verificar_saldo():
                        stop_for_day = True
                        send("🛑 Operaciones detenidas por saldo insuficiente.")
            
            # Detectar transición a fin de sesión para enviar resumen
            if sesion_anterior and not sesion_activa_ahora and risk.trades_hoy > 0:
                enviar_resumen_diario()
                # Reiniciar banderas al final del día
                bot_paused = False
                stop_for_day = False
                trade_allowed_today = True
                last_signal_time = None
                inactivity_alerted = False
            
            sesion_anterior = sesion_activa_ahora

            if sesion_activa_ahora and trade_allowed_today:
                if not notificado_inicio_dia:
                    send("🇪🇺🇺🇸 <b>Bot Activado: EUR/USD</b>\nHorario: 06:15 - 14:45 CDMX (L-V)")
                    notificado_inicio_dia = True

                # Verificar profit target
                if risk.ganancias_hoy >= risk.max_profit_day:
                    if not getattr(risk, '_objetivo_notificado', False):
                        send(f"🎯 <b>Objetivo de ganancia diario alcanzado (${risk.max_profit_day})</b>. Operaciones detenidas hasta mañana.")
                        risk._objetivo_notificado = True
                    time.sleep(60)
                    continue

                # Alarma de inactividad (2 horas sin señales)
                if last_signal_time is not None and not inactivity_alerted:
                    if (time.time() - last_signal_time) > 7200:  # 2 horas
                        send("⚠️ <b>Alerta de inactividad:</b> Han pasado 2 horas sin señales en EUR/USD. El mercado podría estar lateral.")
                        inactivity_alerted = True

                # Evaluar señales
                if not stop_for_day and not bot_paused:
                    for asset in SYMBOLS:
                        v5 = obtener_velas(asset, 5)
                        v1 = obtener_velas(asset, 1)
                        v15 = obtener_velas(asset, 15)
                        v60 = obtener_velas(asset, 60)
                        
                        if not v5 or not v1 or not v15:
                            continue
                        
                        fase, direction, es_turbo, razones, atr = detectar_fase(asset, v5, v1, v15, v60)
                        if fase == "ENTRADA":
                            ejecutar_trade(asset, direction, v1[-2][3], es_turbo, razones, atr)
                            time.sleep(5)
                else:
                    if stop_for_day:
                        print("Bot detenido por comando /stopday.")
                    elif bot_paused:
                        print("Bot pausado por comando /pause.")
                
                seg = datetime.now().second
                time.sleep(61 - seg)
            else:
                if notificado_inicio_dia:
                    notificado_inicio_dia = False
                    if hasattr(risk, '_objetivo_notificado'):
                        del risk._objetivo_notificado
                time.sleep(60)
        except Exception as e:
            print(f"❌ Error en loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    try:
        # Inicializar CSV del día
        init_csv_if_needed()
        # Conectar a Deriv con callback modificado (ver deriv_api)
        api = DerivAPI(DERIV_TOKEN, trade_result_callback)
        # Iniciar hilo de escucha de Telegram
        threading.Thread(target=telegram_polling, daemon=True).start()
        # Iniciar hilo de trading
        threading.Thread(target=analizar, daemon=True).start()
        # Mantener vivo
        while True: time.sleep(10)
    except Exception as e:
        print(f"Error fatal inicio: {e}")
        os._exit(1)
