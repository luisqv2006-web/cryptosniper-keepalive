from firebase_config import db
from datetime import datetime


def actualizar_estado(msg="activo"):
    try:
        db.collection("bot_cache").document("status").set({
            "message": msg,
            "lastUpdate": datetime.utcnow()
        }, merge=True)
        return True
    except Exception as e:
        print("Error actualizar_estado:", e)
        return False


def guardar_macro(data):
    try:
        db.collection("bot_cache").document("macro").set({
            "data": data,
            "timestamp": datetime.utcnow()
        })
        return True
    except Exception as e:
        print("Error guardar_macro:", e)
        return False


def obtener_macro():
    try:
        doc = db.collection("bot_cache").document("macro").get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print("Error obtener_macro:", e)
        return None
