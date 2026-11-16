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
    "apps.reporting",
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
DEMO_INTEGRATIONS = DEBUG and os.getenv("DEMO_INTEGRATIONS", "1") == "1"

# KoBo / kpi integration. For the local kobo-install stack, the nginx port is
# reachable on localhost while the virtual host remains kf.kobo.local.
KOBO_BASE_URL = os.getenv("KOBO_BASE_URL", "http://127.0.0.1")
KOBO_HOST_HEADER = os.getenv("KOBO_HOST_HEADER", "kf.kobo.local")
KOBO_API_TOKEN = os.getenv("KOBO_API_TOKEN", "")
KOBO_VERIFY_TLS = os.getenv("KOBO_VERIFY_TLS", "0") == "1"
KOBO_TIMEOUT = float(os.getenv("KOBO_TIMEOUT", "30"))
KOBO_POLL_INTERVAL = float(os.getenv("KOBO_POLL_INTERVAL", "1"))
KOBO_POLL_TIMEOUT = float(os.getenv("KOBO_POLL_TIMEOUT", "60"))
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
COLLECTION_PROVIDER = os.getenv("COLLECTION_PROVIDER", "kobo")
ODK_BASE_URL = os.getenv("ODK_BASE_URL", "http://central-service:8383")
ODK_PUBLIC_URL = os.getenv("ODK_PUBLIC_URL", "")
ODK_PROJECT_ID = os.getenv("ODK_PROJECT_ID", "1")
ODK_EMAIL = os.getenv("ODK_EMAIL", "")
ODK_PASSWORD = os.getenv("ODK_PASSWORD", "")
ODK_TIMEOUT = float(os.getenv("ODK_TIMEOUT", "90"))
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
