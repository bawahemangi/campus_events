"""
Campus Event Management System - Django Settings
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'campus-events-secret-key-change-in-production-xyz123'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'campus_events.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'campus_events.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

AUTH_USER_MODEL = 'users.CustomUser'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/users/login/'

# ── EMAIL (Gmail SMTP) ────────────────────────────────────────────────
# For testing without real email:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# For production — swap to SMTP and fill in credentials:
EMAIL_BACKEND    = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST       = 'smtp.gmail.com'
EMAIL_PORT       = 587
EMAIL_USE_TLS    = True
EMAIL_HOST_USER  = 'your-email@gmail.com'       # <-- change this
EMAIL_HOST_PASSWORD = 'evoo pesv gsff vhqe'  # Gmail App Password
DEFAULT_FROM_EMAIL = 'CampusEvents <your-email@gmail.com>'
DEFAULT_FROM_EMAIL = 'CampusEvents <noreply@campusevents.local>'

# ── RAZORPAY PAYMENT GATEWAY ─────────────────────────────────────────
# Sign up free at https://dashboard.razorpay.com
# Use TEST keys (rzp_test_...) during development — no real money charged
RAZORPAY_KEY_ID     = 'rzp_test_SctCv30nPnIFUY'   # <-- paste your test key
RAZORPAY_KEY_SECRET = '6ytO0uytHYTiTAm4daHUpmll'    # <-- paste your test secret
RAZORPAY_CURRENCY   = 'INR'

# Site URL for email links
SITE_URL = 'http://127.0.0.1:8000'
SITE_NAME = 'CampusEvents'
