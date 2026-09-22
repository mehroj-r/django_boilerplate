"""Generation-matrix tests.

These assert the invariants that silently broke before there was any CI:
the ASGI entrypoint can import the apps package, the Dockerfile's lock file
exists, and every option combination still produces a coherent project.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from cookiecutter.exceptions import FailedHookException
from cookiecutter.main import cookiecutter

REPO_ROOT = Path(__file__).resolve().parent.parent

API_FRAMEWORKS = ["drf", "django-modern-rest"]
ADMIN_UIS = ["default", "django-unfold"]
BACKGROUND_TASKS = ["none", "celery", "django-q2"]


@pytest.fixture(scope="module")
def default_project(tmp_path_factory):
    out = tmp_path_factory.mktemp("default")
    return Path(cookiecutter(str(REPO_ROOT), no_input=True, output_dir=str(out)))


class TestDefaultProject:
    def test_lock_file_is_generated(self, default_project):
        """The Dockerfile bind-mounts uv.lock and runs `uv sync --locked`."""
        assert (default_project / "uv.lock").exists()

    def test_env_file_has_a_unique_secret_key(self, default_project):
        env = (default_project / ".env").read_text()

        assert "DJANGO_SECRET_KEY=" in env
        assert "change-me-run-just-secret" not in env
        # A "$" here would be eaten by docker compose's .env interpolation.
        secret = next(line for line in env.splitlines() if line.startswith("DJANGO_SECRET_KEY="))
        assert "$" not in secret

    def test_every_entrypoint_bootstraps_the_apps_path(self, default_project):
        """Regression guard for ModuleNotFoundError: No module named 'account'.

        INSTALLED_APPS uses bare labels, so src/apps must be importable before
        django.setup(). Only manage.py used to do this, which left the ASGI and
        WSGI servers -- i.e. production -- unable to boot.
        """
        src = default_project / "src"
        for entrypoint in ("manage.py", "config/server/asgi.py", "config/server/wsgi.py"):
            assert "setup_paths" in (src / entrypoint).read_text(), entrypoint

    def test_healthcheck_path_matches_the_route(self, default_project):
        script = (default_project / "src/scripts/healthcheck.sh").read_text()
        urls = (default_project / "src/api/v1/core/urls/misc.py").read_text()

        assert "/api/v1/health/" in script
        assert 'path("health/"' in urls
        # Without -f, curl exits 0 on a 404 and the check can never fail.
        assert "curl -fsS" in script

    def test_static_root_and_volume_mount_agree(self, default_project):
        compose = (default_project / "docker-compose.yml").read_text()
        dockerfile = (default_project / "Dockerfile").read_text()

        assert "CDN_ROOT=/cdn" in dockerfile
        assert "app_data:/cdn" in compose

    def test_postgres_volume_uses_the_v18_mount_point(self, default_project):
        for name in ("docker-compose.yml", "docker-compose.prod.yml"):
            compose = (default_project / name).read_text()
            assert "postgres_data:/var/lib/postgresql\n" in compose, name

    def test_entrypoint_does_not_invent_migrations(self, default_project):
        entrypoint = (default_project / "src/scripts/entrypoint.sh").read_text()
        commands = [line.strip() for line in entrypoint.splitlines() if not line.strip().startswith("#")]

        assert not any("makemigrations" in line for line in commands), commands
        assert "exec python -m uvicorn config.server.asgi:application \\" in entrypoint

    def test_exception_handler_path_is_importable(self, default_project):
        """import_string splits on the last dot, so it must name a function."""
        settings = (default_project / "src/config/settings/base.py").read_text()
        assert '"EXCEPTION_HANDLER": "core.api.exceptions.api_exception_handler"' in settings


class TestLicense:
    def test_none_removes_the_file(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("nolicense")
        project = Path(
            cookiecutter(
                str(REPO_ROOT),
                no_input=True,
                output_dir=str(out),
                extra_context={"open_source_license": "None"},
            )
        )
        assert not (project / "LICENSE").exists()

    @pytest.mark.parametrize("license_name,marker", [("MIT", "MIT License"), ("Apache-2.0", "Apache License")])
    def test_selected_license_text_is_rendered(self, tmp_path_factory, license_name, marker):
        out = tmp_path_factory.mktemp("license")
        project = Path(
            cookiecutter(
                str(REPO_ROOT),
                no_input=True,
                output_dir=str(out),
                extra_context={"open_source_license": license_name},
            )
        )
        text = (project / "LICENSE").read_text()
        assert marker in text
        # The other licenses' Jinja branches must not leak through.
        assert "{%" not in text


class TestPreGenValidation:
    @pytest.mark.parametrize("slug", ["class", "Bad-Slug", "core", "with-dash"])
    def test_invalid_slugs_are_rejected(self, tmp_path_factory, slug):
        out = tmp_path_factory.mktemp("badslug")
        with pytest.raises(FailedHookException):
            cookiecutter(
                str(REPO_ROOT),
                no_input=True,
                output_dir=str(out),
                extra_context={"project_slug": slug},
            )


class TestOptionMatrix:
    @pytest.mark.parametrize("background_task", BACKGROUND_TASKS)
    def test_background_task_wiring(self, tmp_path_factory, background_task):
        project = _generate(tmp_path_factory, background_task=background_task)
        compose = (project / "docker-compose.yml").read_text()
        compose_prod = (project / "docker-compose.prod.yml").read_text()
        env = (project / ".env.example").read_text()
        deps = _dependencies(project)

        if background_task == "none":
            assert "redis" not in compose
            return

        service = "celery_worker" if background_task == "celery" else "qcluster"
        package = "celery" if background_task == "celery" else "django-q2"

        assert any(dep.startswith(package) for dep in deps), deps
        assert service in compose and service in compose_prod
        # Workers used to inherit config.settings.dev in the production stack.
        assert "DJANGO_SETTINGS_MODULE: config.settings.prod" in compose_prod
        assert "REDIS_URL=redis://redis:6379/0" in env

    @pytest.mark.parametrize("admin_ui", ADMIN_UIS)
    def test_admin_ui_wiring(self, tmp_path_factory, admin_ui):
        project = _generate(tmp_path_factory, admin_ui=admin_ui)
        admin = (project / "src/core/admin.py").read_text()
        settings = (project / "src/config/settings/base.py").read_text()
        active = [line.strip() for line in settings.splitlines() if not line.strip().startswith("#")]

        if admin_ui == "django-unfold":
            assert "from unfold.admin import ModelAdmin" in admin
            assert '"unfold",' in active
            assert any(dep.startswith("django-unfold") for dep in _dependencies(project))
            # contrib apps needing an extra package must stay commented out.
            assert '"unfold.contrib.import_export",' not in active
        else:
            assert "from django.contrib.admin import ModelAdmin" in admin
            assert not any("unfold." in line for line in active)
            assert "UNFOLD_APPS = []" in settings

    @pytest.mark.parametrize("api_framework", API_FRAMEWORKS)
    def test_api_framework_wiring(self, tmp_path_factory, api_framework):
        project = _generate(tmp_path_factory, api_framework=api_framework)
        settings = (project / "src/config/settings/base.py").read_text()
        deps = _dependencies(project)
        auth_urls = (project / "src/api/v1/core/urls/auth.py").read_text()

        if api_framework == "django-modern-rest":
            assert any(dep.startswith("django-modern-rest") for dep in deps), deps
            assert not any(dep.startswith("djangorestframework") for dep in deps), deps
            assert "DMR_SETTINGS" in settings
            assert "REST_FRAMEWORK" not in settings
            # dmr controllers are invisible unless routed through its Router.
            assert "from dmr.routing import Router" in auth_urls
        else:
            assert any(dep.startswith("djangorestframework") for dep in deps), deps
            assert "REST_FRAMEWORK" in settings
            assert "DMR_SETTINGS" not in settings


def _generate(tmp_path_factory, **context):
    out = tmp_path_factory.mktemp("matrix")
    return Path(cookiecutter(str(REPO_ROOT), no_input=True, output_dir=str(out), extra_context=context))


def _dependencies(project) -> list[str]:
    with open(project / "pyproject.toml", "rb") as handle:
        return tomllib.load(handle)["project"]["dependencies"]
