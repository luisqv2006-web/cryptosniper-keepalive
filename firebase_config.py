import os
import firebase_admin
from firebase_admin import credentials, firestore

# ================================
# 🔐 CREDENCIALES DESDE RENDER
# ================================

project_id = os.getenv("FIREBASE_PROJECT_ID")
private_key = os.getenv("FIREBASE_PRIVATE_KEY")
client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

if not project_id or not private_key or not client_email:
    raise ValueError("❌ Credenciales de Firebase NO configuradas en Render")

# ✅ Arreglar saltos de línea del PEM
private_key = private_key.replace("\\n", "\n")

cred = credentials.Certificate({
    "type": "service_account",
    "project_id": project_id,
    "private_key": private_key,
    "client_email": client_email,
    "token_uri": "https://oauth2.googleapis.com/token"
})

firebase_admin.initialize_app(cred)
db = firestore.client()
