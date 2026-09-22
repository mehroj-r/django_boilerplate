"""Validate the cookiecutter context before anything is written to disk.

Catching a bad slug here produces one clear message instead of an import error
somewhere deep in Django's app loading.
"""

from __future__ import annotations

import keyword
import re
import sys

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
DISTRIBUTION_NAME = "{{ cookiecutter.distribution_name }}"
DOCKER_NAME_PREFIX = "{{ cookiecutter.docker_name_prefix }}"

# Names that would shadow a module the generated project imports.
RESERVED_SLUGS = frozenset(
    {
        "account",
        "api",
        "apps",
        "config",
        "core",
        "django",
        "test",
        "tests",
    }
)

DOCKER_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_project_slug() -> None:
    if not PROJECT_SLUG.isidentifier():
        fail(f"project_slug '{PROJECT_SLUG}' is not a valid Python module name (letters, digits, underscores).")
    if keyword.iskeyword(PROJECT_SLUG):
        fail(f"project_slug '{PROJECT_SLUG}' is a Python keyword.")
    if PROJECT_SLUG != PROJECT_SLUG.lower():
        fail(f"project_slug '{PROJECT_SLUG}' must be lowercase.")
    if PROJECT_SLUG in RESERVED_SLUGS:
        fail(f"project_slug '{PROJECT_SLUG}' collides with a module the template already ships.")


def validate_docker_names() -> None:
    for label, value in (("distribution_name", DISTRIBUTION_NAME), ("docker_name_prefix", DOCKER_NAME_PREFIX)):
        if not DOCKER_NAME_RE.match(value):
            fail(f"{label} '{value}' must start with a letter or digit and contain only [a-z0-9._-].")


def main() -> int:
    validate_project_slug()
    validate_docker_names()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
