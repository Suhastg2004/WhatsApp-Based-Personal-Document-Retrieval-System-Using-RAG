"""Django settings for the WhatsApp Meta Backend."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the bot/ root (shared with the RAG service)
_env_path = BASE_DIR.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# --- Django core ---
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
    if h.strip()
]
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Kolkata")

# --- Meta WhatsApp Cloud API ---
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID", "")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "")
META_VALIDATE_SIGNATURE = os.environ.get("META_VALIDATE_SIGNATURE", "false").lower() in ("true", "1", "yes")
META_API_VERSION = os.environ.get("META_API_VERSION", "v21.0")

# --- RAG Service ---
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8001")
RAG_REQUEST_TIMEOUT = int(os.environ.get("RAG_REQUEST_TIMEOUT", "60"))

# --- Twilio WhatsApp (Sandbox) ---
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBERS = [
    n.strip() for n in os.environ.get("TWILIO_WHATSAPP_NUMBERS", "").split(",") if n.strip()
]
TWILIO_SANDBOX_JOIN_CODE = os.environ.get("TWILIO_SANDBOX_JOIN_CODE", "")
TWILIO_VALIDATE_SIGNATURE = os.environ.get("TWILIO_VALIDATE_SIGNATURE", "false").lower() in ("true", "1", "yes")

# --- RAG query settings ---
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "4"))

# --- Validate required vars in production ---
if not DEBUG:
    _required = ["META_ACCESS_TOKEN", "META_PHONE_NUMBER_ID", "META_APP_SECRET", "META_VERIFY_TOKEN"]
    _missing = [v for v in _required if not os.environ.get(v)]
    if _missing:
        sys.exit(f"ERROR: Missing required environment variables: {', '.join(_missing)}")

# --- Application definition ---
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "users",
    "documents",
    "messaging",
    "rag_client",
    "webhook",
    "twilio_app",
    "onboarding",
    "health",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(levelname)s %(name)s :: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
