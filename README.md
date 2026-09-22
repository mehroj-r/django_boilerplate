# 🚀 Django Boilerplate

A cookiecutter template for production-ready Django REST APIs. Answer a few
prompts and you get a project that builds, boots and passes its own test suite.

```bash
uvx cookiecutter gh:mehroj-r/django_boilerplate --checkout drf
cd <your_project_slug>
just up && just health
```

---

## What you choose

| Prompt | Options |
|---|---|
| `api_framework` | `drf` (Django REST Framework + SimpleJWT), `django-modern-rest` (typed controllers, msgspec) |
| `admin_ui` | `default`, `django-unfold` |
| `background_task` | `none`, `celery`, `django-q2` |
| `open_source_license` | `None`, `MIT`, `Apache-2.0`, `GPL-3.0` |

Every combination is exercised in CI: generated, installed, checked, tested and
linted. The default combination additionally gets a `docker compose up` smoke
test that curls the healthcheck.

## What you get

- Layered `src/{api,apps,config,core}` with versioned API routing
- Custom `User` model, JWT auth with rotating + blacklisted refresh tokens
- Consistent `{success, message, data}` response envelope
- Soft deletes with matching admin actions
- OpenAPI schema + Swagger UI + Redoc
- Multi-stage Dockerfile, separate dev/prod compose stacks, health-gated startup
- `pytest` suite, `ruff` config, `Justfile`, GitHub Actions deploy workflows
- `just startapp <name>` — scaffolds the app *and* routes its URLs

---

## Repository layout

This repo is the template itself, on the `drf` branch.

```
cookiecutter.json              # the prompts
hooks/
├── pre_gen_project.py         # validates the slug before anything is written
├── post_gen_project.py        # applies option patches, seeds .env, runs `uv lock`
├── patching/                  # the patch engine (ordering, ops, dependency edits)
├── admin_ui/ api_framework/ background_task/
│                              # one package per option: patches.py + snippets/
└── ...
{{cookiecutter.project_slug}}/ # the project that gets rendered
scripts/generate-project.py    # render into a directory root (no nested folder)
tests/                         # the template's own test suite
```

### How options are applied

The rendered project is the `drf` + `default` + `none` combination. Anything
else is applied afterwards by `post_gen_project.py` as an ordered set of
`PatchSpec`s: each declares an id, a priority, optional `after` dependencies and
optional `conflicts`. `hooks/patching/engine.py` topologically sorts them;
`ops.py` performs anchored edits that are idempotent via a `marker`.

Dependency edits go through `hooks/patching/deps.py`, which matches on the
package name and inserts against a marker comment — so bumping a version in
`{{cookiecutter.project_slug}}/pyproject.toml` cannot break generation.

---

## Working on the template

```bash
uv sync
just test-template   # patch engine + generation matrix
just test            # generate into ./build and run that project's tests
just lint            # ruff + ty
just clean
```

Generating a project runs `uv lock` in it, so `uv` must be installed.

### Adding an option

1. Add the choice to `cookiecutter.json`.
2. Create `hooks/<group>/<option>/` with `patches.py` (exposing `get_patches()`)
   and a `snippets/` directory.
3. Wire it into `collect_patches()` in `hooks/post_gen_project.py`.
4. Add a case to `TestOptionMatrix` in `tests/test_generate.py` and to the CI
   matrix in `.github/workflows/ci.yml`.

Anchor patches on marker comments or package names, never on a pinned version
string — that is what made earlier versions of this template break on a routine
dependency bump.

---

## Branches

| Branch | Contents |
|---|---|
| `drf` | The maintained template. Start here. |
| `drf_aiogram` | Older variant bundling an aiogram Telegram bot. Unmaintained. |
| `master` | This README only. |

---

## License

MIT. Generated projects get the license you select at prompt time.
