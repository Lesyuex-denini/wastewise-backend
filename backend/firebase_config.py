import os
import firebase_admin
from firebase_admin import credentials, firestore

# Try to load path from environment variable first
cred_path = os.getenv("FIREBASE_CREDENTIALS_JSON_PATH")

if cred_path and os.path.exists(cred_path):
    service_account_path = cred_path
else:
    # Fallback: local development path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    service_account_path = os.path.join(BASE_DIR, "serviceAccountKey.json")

# Initialize Firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate(service_account_path)
    firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()
