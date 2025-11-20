# ------------------------------------
# STATS SYSTEM — CRYPTOSNIPER FX
# Guarda rendimiento, winrate y reportes diarios
# ------------------------------------

import json
from datetime import datetime
import os

RUTA = "stats.json"

# ------------------------------------
# Cargar archivo o crear uno
# ------------------------------------
def cargar_stats():
    if not os.path.exists(RUTA):
        data = {
            "operaciones": [],
            "wins": 0,
            "loss": 0,
            "total": 0
        }
        guardar_stats(data)
        return data
    
    with open(RUTA, "r") as file:
        return json.load(file)

# ------------------------------------
# Guardar archivo
# ------------------------------------
def guardar_stats(data):
    with open(RUTA, "w") as file:
        json.dump(data, file, indent=4)

# ------------------------------------
# Registrar operación
# direction = BUY/SELL
# result = "win" / "loss" / "pendiente"
# ------------------------------------
def registrar_operacion(direction, price, result="pendiente"):
    data = cargar_stats()

    operacion = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "direccion": direction,
        "precio": price,
        "resultado": result
    }

    data["operaciones"].append(operacion)
    data["total"] += 1

    guardar_stats(data)

# ------------------------------------
# Marcar operación como Win/Loss
# (Opcional si luego conectamos API de resultados reales)
# ------------------------------------
def actualizar_resultado(index, result):
    data = cargar_stats()

    if index < len(data["operaciones"]):
        data["operaciones"][index]["resultado"] = result
        
        if result == "win":
            data["wins"] += 1
        elif result == "loss":
            data["loss"] += 1
        
        guardar_stats(data)

# ------------------------------------
# Enviar resumen diario al grupo
# ------------------------------------
def resumen_diario(send_func):
    data = cargar_stats()

    if data["total"] == 0:
        send_func("📊 Hoy no hubo operaciones.")
        return

    winrate = (data["wins"] / data["total"]) * 100 if data["total"] > 0 else 0

    mensaje = f"""
📅 <b>RESUMEN DIARIO — CryptoSniper FX</b>

📌 Total operaciones: {data["total"]}
🟢 Ganadas: {data["wins"]}
🔴 Perdidas: {data["loss"]}
📈 Winrate: {winrate:.2f}%

🧠 Recuerda: calidad > cantidad.
"""

    send_func(mensaje)
