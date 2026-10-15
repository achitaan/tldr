"""Local-only study workspace configuration. Secrets never enter serialized status."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get('TLDR_DATA_DIR', BASE_DIR / 'local_data')).resolve()
DATA_ROOT.mkdir(parents=True, exist_ok=True)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or secrets.token_urlsafe(48)
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']
INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.auth', 'rest_framework', 'study']
MIDDLEWARE = ['study.middleware.LocalOnlyMiddleware', 'django.middleware.security.SecurityMiddleware', 'django.middleware.common.CommonMiddleware']
ROOT_URLCONF = 'tldr_backend.urls'
WSGI_APPLICATION = 'tldr_backend.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': DATA_ROOT / 'study.sqlite3', 'OPTIONS': {'timeout': 30, 'transaction_mode': 'IMMEDIATE'}}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
MEDIA_ROOT = DATA_ROOT / 'media'
MEDIA_URL = '/media/'
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': [], 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'], 'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer']}
DATA_UPLOAD_MAX_MEMORY_SIZE = 22 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
LOCAL_ORIGINS = {'http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:4173', 'http://127.0.0.1:4173'}
LOCAL_ORIGINS.update({'http://localhost:8765','http://127.0.0.1:8765'})
