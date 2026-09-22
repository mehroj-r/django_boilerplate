from .base import *  # noqa: F403

DEBUG = False

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- HTTPS / proxy ----------------------------------------------------------
# The app runs behind a reverse proxy that terminates TLS, so trust its header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)  # noqa: F405

# --- HSTS -------------------------------------------------------------------
# Starts at 0 so a misconfigured first deploy cannot pin browsers to HTTPS for a
# domain you do not yet serve over TLS. Raise to 31536000 once you are sure.
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0, cast=int)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)  # noqa: F405
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=False, cast=bool)  # noqa: F405

# --- Cookies ----------------------------------------------------------------
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=csv_list)  # noqa: F405

# --- Misc hardening ---------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
