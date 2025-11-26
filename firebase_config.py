import firebase_admin
from firebase_admin import credentials, firestore

# =========================================
# CONFIGURACIÓN FIREBASE
# =========================================

cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "TU_PROJECT_ID",
    "private_key_id": "TU_PRIVATE_KEY_ID",
    "private_key": "TU_PRIVATE_KEY",
    "client_email": "TU_CLIENT_EMAIL",
    "client_id": "TU_CLIENT_ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "TU_CLIENT_CERT_URL"
})

firebase_admin.initialize_app(cred)
db = firestore.client()
