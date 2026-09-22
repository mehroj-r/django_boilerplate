from .base import *  # noqa: F403

# Only debug-only tooling is gated below; JWT and CORS live in base.py.

CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)  # noqa: F405

if DEBUG:  # noqa: F405
    INSTALLED_APPS += [  # noqa: F405
        "debug_toolbar",
        "django_extensions",
        "query_counter",
    ]

    MIDDLEWARE += [  # noqa: F405
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "query_counter.middleware.DjangoQueryCounterMiddleware",
    ]

    INTERNAL_IPS = ["127.0.0.1"]
