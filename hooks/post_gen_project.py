from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.dont_write_bytecode = True

if TYPE_CHECKING:
    from patching.engine import PatchSpec

ADMIN_UI = "{{ cookiecutter.admin_ui }}"
API_FRAMEWORK = "{{ cookiecutter.api_framework }}"
BACKGROUND_TASK = "{{ cookiecutter.background_task }}"
DOCKER_NAME_PREFIX = "{{ cookiecutter.docker_name_prefix }}"
OPEN_SOURCE_LICENSE = "{{ cookiecutter.open_source_license }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
REPO_DIR = "{{ cookiecutter._repo_dir }}"
TEMPLATE_REF = "{{ cookiecutter._template }}"


def remove_license_if_none() -> None:
    if OPEN_SOURCE_LICENSE == "None":
        Path("LICENSE").unlink(missing_ok=True)


def generate_secret_key() -> str:
    """Generate a SECRET_KEY that is safe to store in a .env file.

    Django's own get_random_secret_key() can emit `$`, which docker compose
    treats as variable interpolation when it reads .env -- the key would be
    silently truncated. A URL-safe token avoids every character with meaning
    to compose, dotenv or a shell, at equal entropy.
    """
    return secrets.token_urlsafe(64)


def write_env_file() -> None:
    """Seed .env from .env.example with a unique SECRET_KEY.

    settings.base requires DJANGO_SECRET_KEY with no fallback, so a generated
    project would otherwise refuse to start until someone invents one -- and
    the old default ("django-insecure-change-me") silently shipped to
    production when they did not.
    """
    example = Path(".env.example")
    target = Path(".env")
    if not example.exists() or target.exists():
        return

    content = example.read_text(encoding="utf-8").replace(
        "DJANGO_SECRET_KEY=change-me-run-just-secret",
        f"DJANGO_SECRET_KEY={generate_secret_key()}",
    )
    target.write_text(content, encoding="utf-8")
    print("Created .env with a freshly generated DJANGO_SECRET_KEY.")


def write_lock_file() -> None:
    """Resolve uv.lock so `docker build` (which runs `uv sync --locked`) works.

    The lock cannot be committed in the template itself: the unrendered
    pyproject.toml has a Jinja placeholder for its project name.
    """
    if Path("uv.lock").exists():
        return
    if shutil.which("uv") is None:
        print("WARNING: uv not found; run `uv lock` before `docker build` (the Dockerfile needs uv.lock).")
        return

    try:
        subprocess.run(["uv", "lock"], check=True, capture_output=True, text=True, timeout=300)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", "") or exc
        print(f"WARNING: `uv lock` failed, run it manually before `docker build`:\n{detail}")
    else:
        print("Generated uv.lock.")


def resolve_repo_dir() -> Path:
    repo_path = Path(REPO_DIR)
    template_path = Path(TEMPLATE_REF)
    env_pwd = os.environ.get("PWD")

    candidates: list[Path] = []
    if repo_path.is_absolute():
        candidates.append(repo_path)
    if template_path.is_absolute():
        candidates.append(template_path)

    if env_pwd:
        pwd_path = Path(env_pwd).resolve()
        candidates.append(pwd_path / repo_path)
        candidates.append(pwd_path / template_path)

    candidates.append((Path.cwd() / repo_path).resolve())
    candidates.append((Path.cwd() / template_path).resolve())

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return candidates[0]


def bootstrap_hooks_imports() -> None:
    hooks_module_root = resolve_repo_dir() / "hooks"
    if not hooks_module_root.exists():
        raise RuntimeError(f"Cannot locate hooks module root: {hooks_module_root}")

    hooks_path = str(hooks_module_root)
    if hooks_path not in sys.path:
        sys.path.insert(0, hooks_path)


def collect_patches() -> list[PatchSpec]:
    patches: list[PatchSpec] = []

    if ADMIN_UI == "django-unfold" or BACKGROUND_TASK != "none" or API_FRAMEWORK == "django-modern-rest":
        bootstrap_hooks_imports()

    if API_FRAMEWORK == "django-modern-rest":
        from api_framework.django_modern_rest import get_patches as get_dmr_patches

        patches.extend(get_dmr_patches())

    if ADMIN_UI == "django-unfold":
        from admin_ui.unfold import get_patches as get_unfold_patches

        patches.extend(get_unfold_patches())

    if BACKGROUND_TASK == "celery":
        from background_task.celery import get_patches as get_celery_patches

        patches.extend(get_celery_patches(docker_prefix=DOCKER_NAME_PREFIX, project_slug=PROJECT_SLUG))

    if BACKGROUND_TASK == "django-q2":
        from background_task.django_q2 import get_patches as get_q2_patches

        patches.extend(get_q2_patches(docker_prefix=DOCKER_NAME_PREFIX, project_slug=PROJECT_SLUG))

    return patches


def main() -> int:
    remove_license_if_none()

    patches = collect_patches()
    if patches:
        from patching.engine import PatchEngine

        engine = PatchEngine(Path.cwd())
        applied = engine.run(patches)
        print(f"Applied hook patches: {', '.join(applied)}")

    # After the patches: they add deps and env vars these two read.
    write_env_file()
    write_lock_file()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
