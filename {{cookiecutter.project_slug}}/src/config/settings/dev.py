from .base import *  # noqa: F403

# Local development conveniences. Anything that must also hold when DEBUG is
# off (JWT lifetimes, CORS) lives in base.py -- only genuine debug-only tooling
# is gated below.

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
