"""Shared fixtures for the template's own test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / "{{cookiecutter.project_slug}}"

# The hook packages import each other as top-level modules (`from patching...`).
sys.path.insert(0, str(REPO_ROOT / "hooks"))


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def template_dir() -> Path:
    return TEMPLATE_DIR


@pytest.fixture
def generate(tmp_path_factory):
    """Generate a project from the template and return its root directory.

    Results are cached per option-combination for the session, because
    generation runs `uv lock`, which is the slow part.
    """
    from cookiecutter.main import cookiecutter

    cache: dict[tuple, Path] = {}

    def _generate(**context) -> Path:
        key = tuple(sorted(context.items()))
        if key not in cache:
            output_dir = tmp_path_factory.mktemp("generated")
            cache[key] = Path(
                cookiecutter(
                    str(REPO_ROOT),
                    no_input=True,
                    output_dir=str(output_dir),
                    extra_context=context or None,
                )
            )
        return cache[key]

    return _generate
