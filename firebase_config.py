# backend/firebase_config.py
import os
import firebase_admin
from firebase_admin import credentials
from django.conf import settings

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    # Skip if already initialized
    if firebase_admin._apps:
        return
    
    try:
        # Method 1: Use service account JSON file
        service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_PATH', None)
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from service account file")
            return
        
        # Method 2: Use environment variables (using os.environ directly)
        project_id = os.environ.get('FIREBASE_PROJECT_ID')
        private_key_id = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
        private_key = os.environ.get('FIREBASE_PRIVATE_KEY')
        client_email = os.environ.get('FIREBASE_CLIENT_EMAIL')
        client_id = os.environ.get('FIREBASE_CLIENT_ID', '')
        client_cert_url = os.environ.get('FIREBASE_CLIENT_CERT_URL', '')
        
        if all([project_id, private_key_id, private_key, client_email]):
            # Clean the private key - replace literal \n with actual newlines
            if '\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')
            
            cred_dict = {
                "type": "service_account",
                "project_id": project_id,
                "private_key_id": private_key_id,
                "private_key": private_key,
                "client_email": client_email,
                "client_id": client_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": client_cert_url
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from environment variables")
            return
        
        # If we get here, no credentials found
        print("❌ Firebase credentials not found. Available environment variables:")
        print(f"  FIREBASE_PROJECT_ID: {'✅' if project_id else '❌'}")
        print(f"  FIREBASE_CLIENT_EMAIL: {'✅' if client_email else '❌'}")
        print(f"  FIREBASE_PRIVATE_KEY: {'✅' if private_key else '❌'}")
        
        raise Exception("No Firebase credentials found in environment variables")
        
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")
        raise

# Don't auto-initialize here - let Django handle it