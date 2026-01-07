"""
Production settings for Global Banker
"""
import os
from .settings import *

# SECURITY - NEVER CHANGE THESE IN PRODUCTION
DEBUG = False
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Generate new one

ALLOWED_HOSTS = [
    'bvnkpro.com',
    'www.bvnkpro.com',
    '80.78.23.17',
]

# HTTPS Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Database - PostgreSQL only
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'global_banker'),
        'USER': os.environ.get('DB_USER', 'banker'),
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        }
    }
}

# Wallet Security - Encrypt XPUB
from cryptography.fernet import Fernet
from django.core.signing import Signer

# Load encrypted XPUB from environment
ENCRYPTED_XPUB = os.environ.get('ENCRYPTED_XPUB')
XPUB_ENCRYPTION_KEY = os.environ.get('XPUB_ENCRYPTION_KEY')

if ENCRYPTED_XPUB and XPUB_ENCRYPTION_KEY:
    f = Fernet(XPUB_ENCRYPTION_KEY.encode())
    DEFAULT_XPUB = f.decrypt(ENCRYPTED_XPUB.encode()).decode()
else:
    DEFAULT_XPUB = ''  # Will fail gracefully

# Logging - Don't log sensitive data
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'wallet': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Admin security
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')  # Change this
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
