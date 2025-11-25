# ======================================
# STATS SYSTEM — CryptoSniper FX
# Registro de operaciones y resumen diario
# ======================================

import json
import os
from datetime import datetime

RUTA = "stats.json"


# --------------------------------------
# Cargar o crear archivo de estadísticas
# --------------------------------------
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

    with open(RUTA, "r") as f:
        return json.load(f)


# --------------------------------------
# Guardar archivo JSON
# --------------------------------------
def guardar_stats(data):
    with open(RUTA, "w") as f:
        json.dump(data, f, indent=4)


# --------------------------------------
# Registrar operación (pendiente)
# --------------------------------------
def registrar_operacion(direction, price, result="pendiente"):
    data = cargar_stats()

    entrada = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "direccion": direction,
        "precio": price,
        "resultado": result
    }

    data["operaciones"].append(entrada)
    data["total"] += 1

    guardar_stats(data)


# --------------------------------------
# Actualizar operación individual
# (WIN / LOSS)
# --------------------------------------
def actualizar_resultado(index, result):
    data = cargar_stats()

    if index < len(data["operaciones"]):
        data["operaciones"][index]["resultado"] = result

        if result == "win":
            data["wins"] += 1
        elif result == "loss":
            data["loss"] += 1

        guardar_stats(data)


# --------------------------------------
# Resumen diario
# --------------------------------------
def resumen_diario(send_func):
    data = cargar_stats()

    total = data["total"]
    wins = data["wins"]
    loss = data["loss"]

    if total == 0:
        send_func("📊 Hoy no hubo operaciones.")
        return

    winrate = (wins / total) * 100 if total > 0 else 0

    mensaje = f"""
📅 <b>RESUMEN DIARIO — CryptoSniper FX</b>

📌 Operaciones totales: {total}
🟢 Ganadas: {wins}
🔴 Perdidas: {loss}
📈 Winrate: {winrate:.2f}%

Sigue avanzando, esto es de disciplina. ⚡
"""

    send_func(mensaje)
