import json
import os

STATS_FILE = "stats.json"

def cargar_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    with open(STATS_FILE, "r") as f:
        return json.load(f)

def guardar_stats(data):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def actualizar_stats(resultado, profit):
    stats = cargar_stats()

    stats["operaciones_totales"] += 1
    stats["profit_total"] += profit
    stats["ultimo_resultado"] = resultado

    if resultado == "WIN":
        stats["ganadas"] += 1
        stats["racha_actual"] += 1
    else:
        stats["perdidas"] += 1
        stats["racha_actual"] = 0

    guardar_stats(stats)

def obtener_status():
    stats = cargar_stats()

    total = stats["operaciones_totales"]
    winrate = (stats["ganadas"] / total * 100) if total > 0 else 0

    return f"""
📊 <b>Estado del Bot — CryptoSniper FX</b>

🧮 Operaciones: {total}
🏆 Ganadas: {stats['ganadas']}
💔 Perdidas: {stats['perdidas']}
📈 Winrate: {winrate:.2f}%
💰 Profit total: ${stats['profit_total']:.2f}
🔥 Racha actual: {stats['racha_actual']}
"""
