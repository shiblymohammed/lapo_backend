from django.apps import AppConfig
import firebase_admin
from firebase_admin import credentials
import os


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'
    
    def ready(self):
        """Initialize Firebase Admin SDK when Django starts (optional)"""
        # Get credentials path from environment
        creds_path = os.getenv('FIREBASE_CREDENTIALS_PATH', '')
        
        # Skip if not provided
        if not creds_path:
            print("ℹ️  Firebase credentials not provided - Firebase authentication disabled")
            return
        
        # Skip if already initialized
        if firebase_admin._apps:
            return
        
        # Make path absolute if it's relative
        if not os.path.isabs(creds_path):
            from django.conf import settings
            creds_path = os.path.join(settings.BASE_DIR, creds_path)
        
        # Check if file exists
        if not os.path.exists(creds_path):
            print(f"⚠️  Firebase credentials file not found: {creds_path}")
            print("ℹ️  Firebase authentication disabled")
            return
        
        try:
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(creds_path)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully")
        except Exception as e:
            print(f"⚠️  Firebase initialization failed: {e}")
            print("ℹ️  Firebase authentication disabled")
