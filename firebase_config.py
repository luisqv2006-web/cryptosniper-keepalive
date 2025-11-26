import os
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "cryptosniper-keepalive-1",
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": "firebase-adminsdk-fbsvc@cryptosniper-keepalive-1.iam.gserviceaccount.com",
    "token_uri": "https://oauth2.googleapis.com/token",
})

firebase_admin.initialize_app(cred)
db = firestore.client()
