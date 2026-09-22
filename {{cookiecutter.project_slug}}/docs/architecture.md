# Architecture notes

## Why `api/` and `apps/` are separate

`apps/` holds Django apps: models, migrations, admin, domain logic. `api/` holds
the HTTP layer: urls, views, serializers, versioned under `api/v1/`, `api/v2/`, …

The split means a second API version reuses the same models instead of forking
them, and domain code never imports DRF. `just startapp <name>` scaffolds both
halves and wires them together.

## The `sys.path` arrangement

`INSTALLED_APPS` lists apps by bare label (`"account"`), which keeps app labels,
migration module paths and `AUTH_USER_MODEL` short. The cost is that
`src/apps` must be importable before `django.setup()`.

`config/bootstrap.py` does that, and `manage.py`, `config/server/asgi.py` and
`config/server/wsgi.py` all call `setup_paths()` first. Miss it in one
entrypoint and that process dies with `ModuleNotFoundError: No module named
'account'` — which is exactly what happens if you add a new entrypoint and
forget. `src/tests/` is covered by `pythonpath` in `pyproject.toml`.

If you prefer no path manipulation, switch `INSTALLED_APPS` to `"apps.account"`
and set `label` on each `AppConfig`.

## Settings layering

```
base.py     everything shared, all env-driven
 ├── dev.py   debug toolbar, django-extensions, query counter (only when DEBUG)
 └── prod.py  HTTPS, HSTS, secure cookies, manifest static storage
```

Settings that must hold regardless of `DEBUG` — JWT lifetimes, CORS, caches —
belong in `base.py`. Putting them under `if DEBUG` means a container started
with `DEBUG=False` silently loses them.

## Response envelope

`core.api.views.CustomResponseMixin.finalize_response` wraps view output. It
skips responses that already contain `success` and `message`, which is how
paginated list responses (built by `CustomPagination`) pass through untouched,
and skips 204/205/304, which must have no body.

Errors are shaped by `core.api.exceptions.api_exception_handler`. That setting
is resolved with `import_string`, which splits on the **last** dot — so it must
name a module-level function. Pointing it at `SomeClass.method` fails to import
and DRF quietly falls back to raising, turning every 400 and 401 into a 500.

## Soft deletes and the user model

`core.models.SoftDeleteModel` wraps `django-soft-delete`. `restore()` defaults to
`strict=True`, refusing to restore a row referenced by a model that is not
itself soft-deletable. `account.User` overrides that default to `strict=False`
because `django.contrib.admin.LogEntry` always has a foreign key to the user
model. Domain models keep the strict default.
