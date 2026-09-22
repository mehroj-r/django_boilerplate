from __future__ import annotations

from patching.deps import add_dependencies
from patching.engine import PatchSpec
from patching.ops import FilePatcher


def read_snippet(filename: str) -> str:
    from pathlib import Path

    SNIPPETS_DIR = Path(__file__).resolve().parent / "snippets"
    return (SNIPPETS_DIR / filename).read_text(encoding="utf-8").rstrip("\n")


def apply_dependencies(patcher: FilePatcher) -> None:
    add_dependencies(patcher, "django-q2>=1.7.5", "redis>=5.2.1")


def apply_settings(patcher: FilePatcher, project_slug: str) -> None:
    q2_settings = read_snippet("q2_settings.txt").replace("{{ cookiecutter.project_slug }}", project_slug)

    patcher.ensure_insert_after(
        "src/config/settings/base.py",
        '    "django_softdelete",\n',
        '    "django_q",\n',
        marker='    "django_q",',
    )

    # Appended rather than inserted mid-file so REDIS_URL (defined in the
    # caching block) is already in scope.
    patcher.ensure_contains("src/config/settings/base.py", q2_settings)
    patcher.ensure_contains(".env.example", read_snippet("q2_env.txt"))


def apply_docker(patcher: FilePatcher, docker_prefix: str) -> None:
    q2_docker = read_snippet("q2_docker.txt").replace("{{ cookiecutter.docker_name_prefix }}", docker_prefix)
    q2_docker_prod = read_snippet("q2_docker_prod.txt").replace("{{ cookiecutter.docker_name_prefix }}", docker_prefix)

    patcher.ensure_insert_before(
        "docker-compose.yml",
        "  web:\n",
        f"{q2_docker}\n\n",
        marker=f'    container_name: "{docker_prefix}-redis-dev"',
    )

    patcher.ensure_insert_before(
        "docker-compose.prod.yml",
        "  web:\n",
        f"{q2_docker_prod}\n\n",
        marker=f'    container_name: "{docker_prefix}-redis-prod"',
    )

    patcher.ensure_insert_after(
        "docker-compose.yml",
        "  app_data:\n",
        "  redis_data:\n",
        marker="  redis_data:",
    )

    patcher.ensure_insert_after(
        "docker-compose.prod.yml",
        "  app_data:\n",
        "  redis_data:\n",
        marker="  redis_data:",
    )


def apply_docs(patcher: FilePatcher) -> None:
    q2_docs = read_snippet("q2_docs.txt")
    patcher.create_file("docs/django_q2.md", q2_docs)


def get_patches(docker_prefix: str, project_slug: str) -> list[PatchSpec]:
    return [
        PatchSpec(
            patch_id="background_task.django_q2.dependencies",
            apply=apply_dependencies,
            priority=10,
        ),
        PatchSpec(
            patch_id="background_task.django_q2.settings",
            apply=lambda p: apply_settings(p, project_slug),
            priority=20,
        ),
        PatchSpec(
            patch_id="background_task.django_q2.docker",
            apply=lambda p: apply_docker(p, docker_prefix),
            priority=30,
        ),
        PatchSpec(
            patch_id="background_task.django_q2.docs",
            apply=apply_docs,
            priority=40,
        ),
    ]
