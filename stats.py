import json
import os
from datetime import datetime

FILE = "stats.json"

def _load():
    if not os.path.exists(FILE):
        return {"operaciones": []}
    with open(FILE, "r") as f:
        return json.load(f)

def _save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

def registrar_operacion(direction, price, result):
    data = _load()
    data["operaciones"].append({
        "t": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dir": direction,
        "price": price,
        "res": result
    })
    data["operaciones"] = data["operaciones"][-500:]
    _save(data)
