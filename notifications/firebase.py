# notifications/firebase.py

import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

# Initialize Firebase
if not firebase_admin._apps:
    # Check if we have the individual environment variables
    if os.environ.get('FIREBASE_TYPE') and os.environ.get('FIREBASE_PROJECT_ID'):
        logger.info("Initializing Firebase with environment variables")
        
        # Build the credentials dict from environment variables
        cred_dict = {
            "type": os.environ.get('FIREBASE_TYPE'),
            "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
            "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
            "auth_uri": os.environ.get('FIREBASE_AUTH_URI'),
            "token_uri": os.environ.get('FIREBASE_TOKEN_URI'),
            "auth_provider_x509_cert_url": os.environ.get('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
            "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_X509_CERT_URL'),
            "universe_domain": os.environ.get('FIREBASE_UNIVERSE_DOMAIN')
        }
        
        try:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully with environment variables")
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
    else:
        # Local development - use file
        from pathlib import Path
        BASE_DIR = Path(__file__).resolve().parent.parent
        SERVICE_ACCOUNT_PATH = BASE_DIR / 'firebase-service-account.json'
        
        if SERVICE_ACCOUNT_PATH.exists():
            try:
                cred = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized with service account file")
            except Exception as e:
                logger.error(f"Firebase initialization failed: {e}")
        else:
            logger.warning("Firebase not configured - notifications disabled")

def send_push_notification(token, title, body, data=None):
    """Send a push notification to a single device token."""
    if not token:
        return None
    
    if not firebase_admin._apps:
        print("Firebase not initialized, skipping notification")
        return None

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon='icon-192x192.png',
                    badge='icon-72x72.png',
                    vibrate=[200, 100, 200],
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link='https://food-xi-ochre.vercel.app/'
                ),
            ),
        )
        response = messaging.send(message)
        print("notification sent")
        
        return response
    except messaging.UnregisteredError:
        return 'unregistered'
    except Exception as e:
        print(f'FCM send error: {e}')
        return None

def send_push_to_multiple(tokens, title, body, data=None):
    """Send the same notification to multiple device tokens."""
    if not tokens:
        return
    
    if not firebase_admin._apps:
        print("Firebase not initialized, skipping notifications")
        return

    valid_tokens = [t for t in tokens if t]
    if not valid_tokens:
        return

    batch_size = 500
    for i in range(0, len(valid_tokens), batch_size):
        batch = valid_tokens[i:i + batch_size]
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={k: str(v) for k, v in (data or {}).items()},
                tokens=batch,
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon='icon-192x192.png',
                        badge='icon-72x72.png',
                        vibrate=[200, 100, 200],
                    ),
                    fcm_options=messaging.WebpushFCMOptions(
                        link='https://food-xi-ochre.vercel.app/'
                    ),
                ),
            )
            messaging.send_each_for_multicast(message)
            print(f"Sending to {len(valid_tokens)} tokens")
        except Exception as e:
            print(f'FCM multicast error: {e}')