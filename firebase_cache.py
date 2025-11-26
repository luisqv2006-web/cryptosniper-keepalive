# ================================
# 🔥 FIREBASE CACHE SYSTEM
# ================================

from firebase_config import db
import time

COLLECTION = "bot_cache"
DOC = "status"

def save_cache(data: dict):
    """Guarda datos del bot en Firestore."""
    data["timestamp"] = time.time()
    db.collection(COLLECTION).document(DOC).set(data)

def load_cache():
    """Lee la memoria del bot desde Firestore."""
    doc = db.collection(COLLECTION).document(DOC).get()
    if doc.exists:
        return doc.to_dict()
    return {}

def update_field(key, value):
    db.collection(COLLECTION).document(DOC).update({key: value})
