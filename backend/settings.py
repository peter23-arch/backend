# backend/backend/settings.py
import os
from pathlib import Path
from datetime import timedelta
from decouple import config
import dj_database_url
from dotenv import load_dotenv 

# Load environment variables from .env file

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-0$4*h27i2gq&f0)66w7h)iux2l4@w+xv7u2miv_t0c7iogvprf'
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
# DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://semifitted-neymar-granular.ngrok-free.dev',
    # Add other trusted origins if needed
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    "http://food-xi-ochre.vercel.app",
    "https://food-xi-ochre.vercel.app",
    "http://localhost:5173/",
    "http://localhost:5174",
    "https://foodcourt-production.up.railway.app",
]
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # 'channels',
    # Our apps
    'users',
    'restaurants',
    'menu',
    'orders',
    'notifications',
    'reviews',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'
# ASGI_APPLICATION = 'backend.asgi.application'

# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer',
#         'CONFIG': {
#             "allowed_origins": [
#                 "https://food-xi-ochre.vercel.app",
#                 "https://semifitted-neymar-granular.ngrok-free.dev",
#             ],
#         },
#     }
# }
# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


DATABASES = {
    'default': dj_database_url.config(default=os.environ.get("DATABASE_URL"))
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# For development, serve static files
if DEBUG:
    STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

    
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' 
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'
# CORS settings - Add these configurations
# In settings.py, replace your CORS configuration with:

# Remove or comment out CORS_ALLOW_ALL_ORIGINS
# CORS_ALLOW_ALL_ORIGINS = DEBUG  # Remove this line

# Explicitly set allowed origins
CORS_ALLOWED_ORIGINS = [
    "https://food-xi-ochre.vercel.app",
    "http://food-xi-ochre.vercel.app",
    "https://semifitted-neymar-granular.ngrok-free.dev",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://foodcourt-production.up.railway.app",
]

# If you need to allow credentials (cookies, authorization headers)

# CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Make sure these methods are allowed
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
# Email configuration — uses Gmail SMTP

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='foodie <praisepetr23@gmail.com>')


FIREBASE_SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, 'firebase-service-account.json')
# OR use environment variables (more secure):
FIREBASE_SERVICE_ACCOUNT_TYPE = os.environ.get('FIREBASE_TYPE', 'service_account')
FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID')
FIREBASE_PRIVATE_KEY_ID = os.environ.get('FIREBASE_PRIVATE_KEY_ID')
FIREBASE_PRIVATE_KEY = os.environ.get('FIREBASE_PRIVATE_KEY')
FIREBASE_CLIENT_EMAIL = os.environ.get('FIREBASE_CLIENT_EMAIL')
FIREBASE_CLIENT_ID = os.environ.get('FIREBASE_CLIENT_ID')
FIREBASE_CLIENT_CERT_URL = os.environ.get('FIREBASE_CLIENT_CERT_URL')
# Frontend URL — used in password reset emails
FRONTEND_URL = config('FRONTEND_URL', default='https://food-xi-ochre.vercel.app')
# ADMIN_SETUP_KEY = config('ADMIN_SETUP_KEY', default='PETERPRAISE')
ADMIN_SETUP_KEY = 'PETERPRAISE'