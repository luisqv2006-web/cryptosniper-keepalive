import json
import os
from datetime import datetime

FILE = "stats.json"

# Crear archivo si no existe
if not os.path.exists(FILE):
    with open(FILE, "w") as f:
        json.dump({"win":0, "loss":0, "profit":0, "history":[]}, f)

def registrar_resultado(result, profit):
    """Guarda win/loss y ganancia acumulada"""
    with open(FILE, "r") as f:
        data = json.load(f)

    if result == "WIN":
        data["win"] += 1
    else:
        data["loss"] += 1

    data["profit"] += profit

    data["history"].append({
        "result": result,
        "profit": profit,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

    return data


def obtener_balance():
    """Devuelve profit acumulado para crear un balance virtual basado en ganancias."""
    if not os.path.exists(FILE):
        return 0
    with open(FILE, "r") as f:
        data = json.load(f)
    return data.get("profit", 0)
