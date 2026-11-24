import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY", "local-development-only-change-before-deployment"
)
if not DEBUG and SECRET_KEY.startswith("local-development"):
    raise RuntimeError("Set DJANGO_SECRET_KEY outside development")
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.accounts",
    "apps.core",
    "apps.establishments",
    "apps.inspections",
    "apps.integrations",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.getenv("POSTGRES_USER", "mandi"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    if not DEBUG:
        raise RuntimeError("PostgreSQL configuration is required outside development")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kabul"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174"
).split(",")
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_RATES": {"login": "10/min"},
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Licensing credentials stay on the backend.
LICENSING_BASE_URL = os.getenv("LICENSING_BASE_URL", "")
LICENSING_REGISTRATION_API_KEY = os.getenv("LICENSING_REGISTRATION_API_KEY", "")
LICENSING_TIMEOUT = float(os.getenv("LICENSING_TIMEOUT", "15"))

# Collection services remain optional: Mandi starts and serves records during outages.
COLLECTION_PROVIDER = os.getenv("COLLECTION_PROVIDER", "odk")
ODK_BASE_URL = os.getenv("ODK_BASE_URL", "http://central-service:8383")
ODK_PUBLIC_URL = os.getenv("ODK_PUBLIC_URL", "")
ODK_PROJECT_ID = os.getenv("ODK_PROJECT_ID", "1")
ODK_EMAIL = os.getenv("ODK_EMAIL", "")
ODK_PASSWORD = os.getenv("ODK_PASSWORD", "")
ODK_TIMEOUT = float(os.getenv("ODK_TIMEOUT", "90"))
ODK_ENTITY_LIST = os.getenv("ODK_ENTITY_LIST", "establishments").strip()
ODK_ENTITY_BATCH_SIZE = int(os.getenv("ODK_ENTITY_BATCH_SIZE", "250"))
ENTITY_SYNC_INTERVAL = int(os.getenv("ENTITY_SYNC_INTERVAL", "300"))
STATIC_ROOT = BASE_DIR / "staticfiles"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_SSL_REDIRECT = not DEBUG
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]

COLLECTION_PROJECT_ID = os.getenv("COLLECTION_PROJECT_ID", ODK_PROJECT_ID)

# Registration is a separate registry, not the Licensing API.
REGISTRATION_BASE_URL = os.getenv("REGISTRATION_BASE_URL", "")
REGISTRATION_API_KEY = os.getenv("REGISTRATION_API_KEY", "")
REGISTRATION_TIMEOUT = float(os.getenv("REGISTRATION_TIMEOUT", "15"))

REGISTRATION_SYNC_ENABLED = os.getenv("REGISTRATION_SYNC_ENABLED", "1") == "1" and bool(REGISTRATION_BASE_URL and REGISTRATION_API_KEY)
REGISTRATION_SYNC_INTERVAL = int(os.getenv("REGISTRATION_SYNC_INTERVAL", "60"))
REGISTRATION_SYNC_PAGE_SIZE = int(os.getenv("REGISTRATION_SYNC_PAGE_SIZE", "50"))
