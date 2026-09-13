"""
==============================================================================
Touch and Solve Microfinance Co-operative System
Settings Configuration (Beginner-Friendly Learning Project)
==============================================================================
This file contains all the settings and configurations for the Django project.
It follows standard Django best practices with beginner-friendly explanations.
"""

from pathlib import Path
import os
import sys

# -----------------------------------------------------------------------------
# 1. BASE DIRECTORY
# Points to the root folder of our project (where manage.py is located).
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Add the 'apps' folder to Python path so we can import our apps cleanly
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# -----------------------------------------------------------------------------
# 2. SECURITY & ENVIRONMENT
# -----------------------------------------------------------------------------
# SECRET_KEY is used for cryptographic signing in Django sessions and cookies.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-tns-microfinance-cooperative-secret-key-prod-dev-2026')

# DEBUG: Set to True during development so Django shows helpful error tracebacks.
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS: List of domain names/IPs this Django site can serve.
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'http://127.0.0.1',
    'http://localhost',
]

# -----------------------------------------------------------------------------
# SSLCOMMERZ HOSTED PAYMENT GATEWAY (Sandbox & Live)
# -----------------------------------------------------------------------------
SSLCOMMERZ_STORE_ID = os.environ.get('SSLCOMMERZ_STORE_ID', 'tnsco6a9fad1c04883')
SSLCOMMERZ_STORE_PASS = os.environ.get('SSLCOMMERZ_STORE_PASS', 'tnsco6a9fad1c04883@ssl')
SSLCOMMERZ_IS_SANDBOX = os.environ.get('SSLCOMMERZ_IS_SANDBOX', 'True') == 'True'

# -----------------------------------------------------------------------------
# 3. INSTALLED APPS
# Here we register standard Django built-in apps and our custom project apps.
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Built-in Django Applications
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Our Custom Microfinance Apps (under apps/ folder)
    'apps.accounts',      # Authentication, user roles, profile
    'apps.members',       # Member KYC records and officer assignment
    'apps.savings',       # Savings accounts, deposit/withdrawal requests
    'apps.loans',         # Loan products, applications, amortization schedules
    'apps.core',          # Dashboards (Admin/Officer/Member), reports, printing
    'apps.notifications', # In-app alerts, payment confirmations, and system notifications
]

# -----------------------------------------------------------------------------
# 4. MIDDLEWARE
# Functions that process every request/response before reaching views.
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -----------------------------------------------------------------------------
# 5. URLS & TEMPLATES CONFIGURATION
# -----------------------------------------------------------------------------
ROOT_URLCONF = 'tns_microfinance.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Where Django looks for custom HTML files
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Makes request, user, and messages automatically available in all templates
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.notification_context',
            ],
            'builtins': [
                'apps.core.templatetags.currency_tags',
            ],
        },
    },
]

WSGI_APPLICATION = 'tns_microfinance.wsgi.application'

# -----------------------------------------------------------------------------
# 6. DATABASE CONFIGURATION
# We use SQLite for easy, lightweight setup with zero extra configuration.
# -----------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Optional PostgreSQL support if DATABASE_URL environment variable is present
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    except ImportError:
        pass

# -----------------------------------------------------------------------------
# 7. AUTHENTICATION & CUSTOM USER MODEL
# -----------------------------------------------------------------------------
# Tell Django to use our CustomUser model with role support (Admin, Officer, Member)
AUTH_USER_MODEL = 'accounts.CustomUser'

# Password validation rules
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
]

# -----------------------------------------------------------------------------
# 8. INTERNATIONALIZATION & TIMEZONE
# -----------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dhaka'
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# 9. STATIC & MEDIA FILES (CSS, JS, User Uploads)
# -----------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Directory where uploaded member photos and KYC documents are saved
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -----------------------------------------------------------------------------
# 10. AUTHENTICATION REDIRECT URLS
# -----------------------------------------------------------------------------
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
