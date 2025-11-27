from firebase_config import db
from datetime import datetime

def actualizar_estado(msg="activo"):
    if not db:
        return False
    try:
        db.collection("bot_cache").document("status").set({
            "message": msg,
            "lastUpdate": datetime.utcnow()
        }, merge=True)
        return True
    except:
        return False

def guardar_macro(data):
    if not db:
        return False
    try:
        db.collection("bot_cache").document("macro").set({
            "data": data,
            "timestamp": datetime.utcnow()
        })
        return True
    except:
        return False
