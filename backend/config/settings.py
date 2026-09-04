import os
from pathlib import Path
from dotenv import load_dotenv

try:
    import dj_database_url
except ImportError:  # pragma: no cover - optional dependency for production DB config
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS",
                                                   "localhost,127.0.0.1,api.organicemperor.com,admin.organicemperor.com").split(",") if h.strip()]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "django_error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "django-errors.log",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["django_error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "corsheaders", "rest_framework", "accounts", "catalog", "commerce", "archives",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True, "OPTIONS": {"context_processors": [
    "django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL and not DEBUG:
    raise RuntimeError("DATABASE_URL is required in production")

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
    )
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"]["init_command"] = (
        "SET sql_mode='STRICT_TRANS_TABLES'"
    )
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-ca"
TIME_ZONE = "America/Edmonton"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,https://organicemperor.com,https://www.organicemperor.com,https://stagging.organicemperor.com,https://organicarchives.organicemperor.com").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:5173,https://organicemperor.com,https://www.organicemperor.com,https://stagging.organicemperor.com,https://admin.organicemperor.com,https://api.organicemperor.com").split(",") if origin.strip()]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
REST_FRAMEWORK = {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
                  "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
                  "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination", "PAGE_SIZE": 24,
                  "DEFAULT_THROTTLE_RATES": {
                      "authentication": "20/minute",
                      "checkout": "30/minute",
                      "payment": "10/minute",
}}

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox").lower()
COMMERCE_TAX_ADAPTER = os.environ.get(
    "COMMERCE_TAX_ADAPTER", "commerce.tax.UnavailableTaxAdapter"
)
COMMERCE_ALLOW_ZERO_TAX = os.environ.get(
    "COMMERCE_ALLOW_ZERO_TAX", "False").lower() == "true"
AVATAX_ACCOUNT_ID = os.environ.get("AVATAX_ACCOUNT_ID", "")
AVATAX_LICENSE_KEY = os.environ.get("AVATAX_LICENSE_KEY", "")
AVATAX_COMPANY_CODE = os.environ.get("AVATAX_COMPANY_CODE", "")
AVATAX_ENVIRONMENT = os.environ.get("AVATAX_ENVIRONMENT", "sandbox").lower()
AVATAX_ORIGIN_LINE1 = os.environ.get("AVATAX_ORIGIN_LINE1", "")
AVATAX_ORIGIN_CITY = os.environ.get("AVATAX_ORIGIN_CITY", "")
AVATAX_ORIGIN_REGION = os.environ.get("AVATAX_ORIGIN_REGION", "")
AVATAX_ORIGIN_POSTAL_CODE = os.environ.get("AVATAX_ORIGIN_POSTAL_CODE", "")
AVATAX_ORIGIN_COUNTRY = os.environ.get("AVATAX_ORIGIN_COUNTRY", "CA").upper()
