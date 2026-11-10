import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-melonestay-dev-key-change-in-production"

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1:8000"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "accounts",
    "staffs",
    "room_categories",
    "room_masters",
    "ota",
    "tax_master",
    "currency_master",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "PATCH",
    "POST",
    "PUT",
    "OPTIONS",
]

CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
]

STATIC_URL = "/static/"

ROOT_URLCONF = "melonestay.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "melonestay.wsgi.application"

# PostgreSQL Database Configuration
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
JWT_ACCESS_TOKEN_LIFETIME = 60 * 60 * 8

SUPERUSER_API_URL = "https://su.myimc.in/api/superusers/endpoint/MELONESTAY/CYKOWV0Z/"
SUPERUSER_API_TIMEOUT = 5

PROJECT_API_URL = "https://activate.imcbs.com/mobileapp/api/project/melonestay/"
PROJECT_API_TIMEOUT = 2

USER_MASTER_API_URL = "https://centralmastermanagement.imcbs.com/api/user-master/"
USER_MASTER_API_TIMEOUT = 10

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'signup.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}