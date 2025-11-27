import os
import firebase_admin
from firebase_admin import credentials, firestore

private_key = os.getenv("FIREBASE_PRIVATE_KEY")
client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

db = None

try:
    if not private_key or not client_email:
        raise ValueError("Credenciales de Firebase NO configuradas en Render")

    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "cryptosniper-keepalive-1",
        "private_key": private_key.replace("\\n", "\n"),
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    })

    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase conectado correctamente")

except Exception as e:
    print("❌ Firebase DESACTIVADO:", e)
    db = None
