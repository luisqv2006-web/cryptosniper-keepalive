from firebase_config import db
from datetime import datetime
import pytz

mx = pytz.timezone("America/Mexico_City")

def actualizar_estado(message):
    doc = db.collection("bot_cache").document("status")
    doc.set({
        "lastUpdate": datetime.now(mx),
        "message": message
    })

def guardar_macro(asset, tendencia):
    doc = db.collection("bot_cache").document("macro")
    doc.set({
        asset: tendencia,
        "updated": datetime.now(mx)
    }, merge=True)

def obtener_macro(asset):
    doc = db.collection("bot_cache").document("macro").get()
    if doc.exists:
        data = doc.to_dict()
        return data.get(asset)
    return None
