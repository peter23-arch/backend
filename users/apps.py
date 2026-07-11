# users/apps.py
from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        try:
            from firebase_config import initialize_firebase
            initialize_firebase()
        except Exception as e:
            print(f"⚠️ Firebase initialization warning: {e}")
            print("⚠️ Google sign-in will not work until Firebase is properly configured")
            # Don't crash the server