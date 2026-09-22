from datetime import timedelta
from pathlib import Path
from urllib.parse import quote_plus

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("DJANGO_SECRET_KEY")


def csv_list(value: str) -> list[str]:
    """Parse a comma-separated env var, tolerating spaces and trailing commas."""
    return [item.strip() for item in value.split(",") if item.strip()]


ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=csv_list)


def build_database_url() -> str:
    """Compose a Postgres DSN from the POSTGRES_* vars.

    Credentials are percent-encoded so passwords containing ``@ : / #`` survive
    URL parsing. A full ``DATABASE_URL`` always wins if one is provided.
    """
    user = quote_plus(config("POSTGRES_USER"))
    password = quote_plus(config("POSTGRES_PASSWORD"))
    host = config("POSTGRES_HOST", default="localhost")
    port = config("POSTGRES_PORT", default="5432")
    name = config("POSTGRES_DB")
    return f"postgres://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = config("DATABASE_URL", default="") or build_database_url()

UNFOLD_APPS = []

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "drf_standardized_errors",
    "django_softdelete",
]

LOCAL_APPS = [
    "account",
    "core",
]

INSTALLED_APPS = UNFOLD_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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

ASGI_APPLICATION = "config.server.asgi.application"
WSGI_APPLICATION = "config.server.wsgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        url=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locales"]

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# Single root so one volume covers both. /cdn in the container.
CDN_ROOT = Path(config("CDN_ROOT", default=str(BASE_DIR.parent / "cdn")))

STATIC_ROOT = CDN_ROOT / "static"
MEDIA_ROOT = CDN_ROOT / "media"

# Logging
LOGGING_TELEGRAM_BOT_TOKEN = config("LOGGING_TELEGRAM_BOT_TOKEN", default="")
LOGGING_TELEGRAM_CHAT_ID = config("LOGGING_TELEGRAM_CHAT_ID", default="")
# Tracebacks can contain request data; keep them off unless the chat is private.
LOGGING_TELEGRAM_INCLUDE_TRACEBACK = config("LOGGING_TELEGRAM_INCLUDE_TRACEBACK", default=False, cast=bool)
PROJECT_NAME = config("PROJECT_NAME", default="{{ cookiecutter.project_name }}")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_context": {
            "()": "core.utils.logging.RequestContextFilter",
        },
    },
    "formatters": {
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": (
                "%(log_color)s[%(asctime)s] [%(levelname)s] "
                "%(name)s:%(module)s:%(filename)s:%(lineno)d "
                "%(funcName)s | %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "log_colors": {
                "DEBUG": "white",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        },
        # TelegramErrorHandler escapes every value, so only these tags are markup.
        "telegram": {
            "format": (
                "<b>🚨 {{ cookiecutter.project_name }} error alert</b>\n"
                "<b>Level:</b> %(levelname)s\n"
                "<b>Message:</b> %(message)s\n\n"
                "<b>Module:</b> <code>%(module)s:%(filename)s:%(lineno)d</code>\n"
                "<b>Function:</b> <code>%(funcName)s</code>\n\n"
                "<b>User:</b> %(user)s\n"
                "<b>Method:</b> %(method)s\n"
                "<b>Path:</b> %(path)s\n"
                "<b>IP:</b> %(ip)s\n\n"
                "<b>Traceback:</b>\n<pre>%(traceback)s</pre>"
            )
        },
    },
    "handlers": {
        # Console
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
        # Telegram alerts
        "telegram_errors": {
            "level": "ERROR",
            "class": "core.utils.logging.TelegramErrorHandler",
            "bot_token": LOGGING_TELEGRAM_BOT_TOKEN,
            "chat_id": LOGGING_TELEGRAM_CHAT_ID,
            "include_traceback": LOGGING_TELEGRAM_INCLUDE_TRACEBACK,
            "filters": ["request_context"],
            "formatter": "telegram",
        },
    },
    "loggers": {
        # Django internal logs
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Django request errors → TELEGRAM!
        "django.request": {
            "handlers": ["telegram_errors", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        # Universal logger (entire project)
        "": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "core.utils.pagination.CustomPagination",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "core.api.errors.EnvelopedAutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_RATE_ANON", default="60/min"),
        "user": config("THROTTLE_RATE_USER", default="1000/min"),
    },
    "PAGE_SIZE": 10,
    # Must stay drf-standardized-errors' own callable: its AutoSchema compares
    # the view's handler against it by identity and quietly stops documenting
    # error responses if it does not match. Customize via DRF_STANDARDIZED_ERRORS.
    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler",
}

DRF_STANDARDIZED_ERRORS = {
    "EXCEPTION_HANDLER_CLASS": "core.api.exceptions.ApiExceptionHandler",
    "EXCEPTION_FORMATTER_CLASS": "core.api.errors.EnvelopedExceptionFormatter",
    # Without this, unhandled exceptions skip the envelope while DEBUG is on,
    # so dev and prod would disagree on the shape of a 500.
    "ENABLE_IN_DEBUG_FOR_UNHANDLED_EXCEPTIONS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": PROJECT_NAME,
    "DESCRIPTION": "{{ cookiecutter.project_name }} API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v[0-9]+",
    # Replaces drf-spectacular's own enum hook; the error-code enums are built
    # per operation, and its hook warns on every one of them.
    "POSTPROCESSING_HOOKS": ["drf_standardized_errors.openapi_hooks.postprocess_schema_enums"],
    "ENUM_NAME_OVERRIDES": {
        "ValidationErrorEnum": "drf_standardized_errors.openapi_serializers.ValidationErrorEnum.choices",
        "ClientErrorEnum": "drf_standardized_errors.openapi_serializers.ClientErrorEnum.choices",
        "ServerErrorEnum": "drf_standardized_errors.openapi_serializers.ServerErrorEnum.choices",
        "ErrorCode401Enum": "drf_standardized_errors.openapi_serializers.ErrorCode401Enum.choices",
        "ErrorCode403Enum": "drf_standardized_errors.openapi_serializers.ErrorCode403Enum.choices",
        "ErrorCode404Enum": "drf_standardized_errors.openapi_serializers.ErrorCode404Enum.choices",
        "ErrorCode405Enum": "drf_standardized_errors.openapi_serializers.ErrorCode405Enum.choices",
        "ErrorCode406Enum": "drf_standardized_errors.openapi_serializers.ErrorCode406Enum.choices",
        "ErrorCode415Enum": "drf_standardized_errors.openapi_serializers.ErrorCode415Enum.choices",
        "ErrorCode429Enum": "drf_standardized_errors.openapi_serializers.ErrorCode429Enum.choices",
        "ErrorCode500Enum": "drf_standardized_errors.openapi_serializers.ErrorCode500Enum.choices",
    },
}

AUTH_USER_MODEL = "account.User"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS", default=7, cast=int)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- CORS -------------------------------------------------------------------
# Production must list origins explicitly; dev relaxes this.
CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="", cast=csv_list)
CORS_ALLOW_CREDENTIALS = config("CORS_ALLOW_CREDENTIALS", default=False, cast=bool)

# --- Caching ----------------------------------------------------------------
# Not tied to REDIS_URL: throttling reads the cache on every request, so a
# broker outage must not take the API down.
CACHE_URL = config("CACHE_URL", default="")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CACHE_URL,
    }
    if CACHE_URL
    else {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "{{ cookiecutter.project_slug }}",
    }
}

# --- Upload limits ----------------------------------------------------------
DATA_UPLOAD_MAX_MEMORY_SIZE = config("DATA_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024, cast=int)
FILE_UPLOAD_MAX_MEMORY_SIZE = config("FILE_UPLOAD_MAX_MEMORY_SIZE", default=10 * 1024 * 1024, cast=int)

# --- Error reporting --------------------------------------------------------
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=config("SENTRY_ENVIRONMENT", default="development"),
        release=config("SENTRY_RELEASE", default=None),
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.0, cast=float),
        send_default_pii=False,
    )
