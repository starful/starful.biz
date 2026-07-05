"""External service clients (Firebase, Gemini)."""
from __future__ import annotations

import os

import firebase_admin
from firebase_admin import credentials, firestore
from google import genai

db = None
try:
    if not firebase_admin._apps:
        sm_key_path = "/secrets/FIREBASE_KEY"
        if os.path.exists(sm_key_path):
            cred = credentials.Certificate(sm_key_path)
            firebase_admin.initialize_app(cred)
        else:
            firebase_admin.initialize_app()
    db = firestore.client()
except Exception as e:
    print(f"⚠️ Firebase Warning: {e}")

ai_client = None
if os.getenv("GEMINI_API_KEY"):
    ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
