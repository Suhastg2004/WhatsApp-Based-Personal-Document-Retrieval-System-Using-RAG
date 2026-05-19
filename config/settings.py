"""Django settings for the WhatsApp document RAG bot."""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    TWILIO_VALIDATE_SIGNATURE=(bool, True),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-key-change-me")
DEBUG = env("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", default="*").split(",") if h.strip()]

# Trust ngrok / public URL for CSRF on the Twilio webhook page; webhook itself is csrf_exempt.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://127.0.0.1:8000")
CSRF_TRUSTED_ORIGINS = [PUBLIC_BASE_URL] if PUBLIC_BASE_URL.startswith("http") else []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "documents",
    "rag",
    "messaging",
    "onboarding",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25 MB

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# --- Twilio ---
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_NUMBERS = [
    n.strip()
    for n in env("TWILIO_WHATSAPP_NUMBERS", default="").split(",")
    if n.strip()
]
TWILIO_SANDBOX_JOIN_CODE = env("TWILIO_SANDBOX_JOIN_CODE", default="")
TWILIO_VALIDATE_SIGNATURE = env("TWILIO_VALIDATE_SIGNATURE", default=True)

# --- RAG ---
EMBEDDING_MODEL_NAME = env("EMBEDDING_MODEL_NAME", default="sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = env.int("CHUNK_SIZE", default=800)
CHUNK_OVERLAP = env.int("CHUNK_OVERLAP", default=120)
DEFAULT_TOP_K = env.int("DEFAULT_TOP_K", default=4)
MAX_CONTEXT_CHUNKS = env.int("MAX_CONTEXT_CHUNKS", default=4)

GENERATION_BACKEND = env("GENERATION_BACKEND", default="extractive").lower().strip()
GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_MODEL = env("GROQ_MODEL", default="openai/gpt-oss-120b")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(levelname)s %(name)s :: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "rag": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "messaging": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
