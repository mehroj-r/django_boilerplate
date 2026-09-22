# {{ cookiecutter.project_name }}

A production-ready Django REST API: layered project structure, JWT auth, soft
deletes, OpenAPI docs, Docker for dev and prod, and a test suite that runs from
the first commit.

---

## Quickstart

```bash
cp .env.example .env          # already created for you, with a unique SECRET_KEY
just up                       # build + start Postgres and the API
just health                   # -> Healthcheck passed on :8005
```

| What | Where |
|---|---|
| API root | http://localhost:8005/api/v1/ |
| Health probe | http://localhost:8005/api/v1/health/ |
| Swagger UI | http://localhost:8005/api/schema/swagger-ui/ |
| Redoc | http://localhost:8005/api/schema/redoc/ |
| Admin | http://localhost:8005/admin/ |

Create an admin user with `docker compose exec web python manage.py createsuperuser`.

### Without Docker

```bash
uv sync
# point POSTGRES_HOST at a reachable Postgres (`localhost` if you run one yourself)
just migrate
just superuser
just run
```

`just` loads `.env` automatically. Run `just` with no arguments to list every recipe.

---

## Project structure

```
{{ cookiecutter.project_slug }}/
├── Dockerfile                    # multi-stage; INSTALL_DEV=true adds dev deps
├── docker-compose.yml            # dev stack   (project name: <slug>-dev)
├── docker-compose.prod.yml       # prod stack  (project name: <slug>-prod)
├── Justfile                      # every task you need; `just` to list them
├── pyproject.toml / uv.lock      # dependencies, locked
├── docs/                         # deployment and how-to notes
└── src/
    ├── manage.py
    ├── api/                      # HTTP layer only: urls, views, serializers
    │   ├── url_router.py         # mounts /api/v1/, add /api/v2/ here
    │   └── v1/
    │       ├── urls.py           # version root; startapp registers apps here
    │       ├── account/          # per-app API modules
    │       └── core/             # auth + health/test endpoints
    ├── apps/                     # Django apps: models, admin, migrations
    │   └── account/              # the custom User model
    ├── config/
    │   ├── bootstrap.py          # puts src/apps on sys.path (see below)
    │   ├── server/               # asgi.py / wsgi.py
    │   ├── settings/             # base.py -> dev.py / prod.py
    │   └── urls/
    ├── core/                     # shared building blocks (see below)
    ├── scripts/                  # entrypoint.sh, healthcheck.sh
    └── tests/
```

Apps are imported by their bare label (`"account"`, not `"apps.account"`), so
`src/apps` has to be on `sys.path` before `django.setup()`. That is what
`config/bootstrap.py` does, and **every** entrypoint — `manage.py`, `asgi.py`
and `wsgi.py` — calls it. If you add another entrypoint, call it there too.

---

## What `core/` gives you

| Module | Use it for |
|---|---|
| `core.api.views` | `ListAPIView`, `CreateAPIView`, … — same as DRF's, plus the response envelope |
| `core.api.exceptions` | `api_exception_handler`, wired into `REST_FRAMEWORK["EXCEPTION_HANDLER"]` |
| `core.models` | `TimestampedModel`, `SoftDeleteModel`, `BaseModel` |
| `core.admin` | `BaseModelAdmin`, `BaseSoftDeleteModelAdmin` |
| `core.utils.pagination` | `CustomPagination` (`?page=`, `?per_page=`) |
| `core.utils.logging` | console formatter + optional Telegram error alerts |

### Response envelope

```jsonc
// success
{ "success": true,  "message": "OK",  "data": { } }
// list (paginated)
{ "success": true, "message": "OK", "results": [], "total_count": 0,
  "page": 1, "page_count": 1, "per_page": 10 }
```

Errors use the same envelope, with the failure described under `error`:

```jsonc
{
  "success": false,
  "message": "email: This field is required.",
  "error": {
    "type": "validation_error",          // or client_error / server_error
    "errors": [
      { "code": "required", "detail": "This field is required.", "attr": "email" }
    ]
  }
}
```

This error contract is identical whichever `api_framework` you picked, and
`src/tests/test_errors.py` asserts it. Where the shape comes from differs:
`drf-standardized-errors` on the drf side, `Controller.error_model` plus
`format_error` on the django-modern-rest side. Either way `core/api/errors.py`
is the file that defines it, and `core/api/exceptions.py` is where you map your
own exception types into it.

Two honest caveats on django-modern-rest. Success responses are *not* wrapped
there -- `BaseController.ok()` exists if you want to, but endpoints return their
payload directly. And with the msgspec serializer a validation failure reports
only the first bad field, where drf reports all of them at once, because msgspec
stops at the first error.

### Soft deletes

Models inheriting `core.models.SoftDeleteModel` get three managers:

```python
MyModel.objects          # alive rows only (default manager)
MyModel.deleted_objects  # soft-deleted rows only
MyModel.global_objects   # everything
```

`instance.delete()` soft-deletes; `instance.restore()` brings it back. Register
such models with `BaseSoftDeleteModelAdmin` to get restore/hard-delete actions.

---

## Adding an app

```bash
just startapp orders        # or: just startapp orders v2
```

This creates `src/apps/orders/` and `src/api/v1/orders/`, adds `"orders"` to
`LOCAL_APPS`, **and** registers `api/v1/orders/urls.py` under `/api/v1/orders/`.
Then define models and run `just makemigrations orders && just migrate`.

---

## Authentication

JWT via `djangorestframework` + `djangorestframework-simplejwt`.

```http
POST /api/v1/auth/login/     {"username": "...", "password": "..."}
POST /api/v1/auth/refresh/   {"refresh": "..."}
POST /api/v1/auth/verify/    {"token": "..."}
```

Send `Authorization: Bearer <access>` on protected endpoints. Endpoints require
authentication by default (`DEFAULT_PERMISSION_CLASSES`); set
`permission_classes = ()` on a view to make it public.

Refresh tokens rotate and the old one is blacklisted
(`rest_framework_simplejwt.token_blacklist` is installed, so this actually takes
effect). Lifetimes come from `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS`.

---

## Settings

`base.py` holds everything shared; `dev.py` and `prod.py` import it with
`from .base import *`. `DJANGO_SETTINGS_MODULE` defaults to `config.settings.dev`
for `manage.py` and `config.settings.prod` for the ASGI/WSGI servers; both
compose files set it explicitly.

Only genuine debug tooling (debug toolbar, django-extensions, query counter) is
gated behind `if DEBUG` — JWT and CORS configuration applies either way.

All configuration is environment-driven; see `.env.example` for the full list
with comments. The ones you must set before going live:

| Variable | Why |
|---|---|
| `DJANGO_SECRET_KEY` | Generated into `.env` at project creation. Rotate for production. |
| `ALLOWED_HOSTS` | Comma-separated; Django rejects everything else. |
| `CORS_ALLOWED_ORIGINS` | Production sets no default, so browsers are blocked until you list origins. |
| `CSRF_TRUSTED_ORIGINS` | Needed for the admin behind HTTPS. |
| `SECURE_HSTS_SECONDS` | Defaults to `0`. Raise to `31536000` **after** TLS is confirmed. |
| `SENTRY_DSN` | Optional; Sentry initialises only when set. |

Verify with `just check`, which runs Django's deployment checklist.

---

## Testing

```bash
just test              # pytest, needs a reachable Postgres
just check-migrations  # fails if a model change has no migration
just lint              # ruff
```

Tests live in `src/tests/` and use `factory-boy` (`tests/factories.py`).

---

## Deployment

`docker-compose.prod.yml` runs the same image with `config.settings.prod`,
health-gated startup and an explicit bridge network. Publish behind a TLS
terminating reverse proxy; the app trusts `X-Forwarded-Proto`.

The entrypoint runs `migrate` and `collectstatic`, then `exec`s uvicorn (so
signals reach it). It deliberately does **not** run `makemigrations` — migrations
are source code. When several replicas boot together, set `RUN_MIGRATIONS=False`
and apply migrations from a single job.

Static files and uploads are written to `CDN_ROOT` (`/cdn` in the image), which
is where the `app_data` volume is mounted. Keep those in sync if you change one.

GitHub Actions workflows for dev and prod live in `.github/workflows/`; the
secrets they need are documented in `docs/deployment/GITHUB-SECRETS.md`.

---

## Logging

Console logging is colourised. If `LOGGING_TELEGRAM_BOT_TOKEN` and
`LOGGING_TELEGRAM_CHAT_ID` are set, unhandled 500s are pushed to Telegram from a
background thread. Tracebacks are **off** by default
(`LOGGING_TELEGRAM_INCLUDE_TRACEBACK`) because they can contain request data —
turn them on only for a private chat.
