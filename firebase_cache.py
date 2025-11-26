from firebase_config import db
from datetime import datetime

# ================================
# GUARDAR OPERACIÓN EN FIREBASE
# ================================
def guardar_operacion(asset, direction, price, status="pendiente"):
    db.collection("operaciones").add({
        "activo": asset,
        "direccion": direction,
        "precio": price,
        "estado": status,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


# ================================
# ACTUALIZAR RESULTADO (WIN / LOSS)
# ================================
def marcar_resultado(doc_id, resultado, profit):
    db.collection("operaciones").document(doc_id).update({
        "estado": resultado,
        "ganancia": profit
    })


# ================================
# GUARDAR STATUS DEL BOT
# ================================
def guardar_status_bot(status):
    db.collection("status").document("bot").set({
        "estado": status,
        "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
