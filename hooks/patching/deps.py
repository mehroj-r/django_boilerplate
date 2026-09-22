"""Version-agnostic dependency editing for generated ``pyproject.toml`` files.

Patches used to anchor on the exact pinned requirement string (for example
``'    "django-filter>=25.1",\\n'``), so bumping any version in the template's
pyproject.toml silently broke project generation with a PatchOperationError.
These helpers match on the package name only, and insert against a stable
marker comment.
"""

from __future__ import annotations

import re

from .ops import FilePatcher

PYPROJECT = "pyproject.toml"

DEPENDENCY_MARKER = "    # >>> optional dependencies are inserted above this marker by the template\n"
DEV_DEPENDENCY_MARKER = "    # >>> optional dev dependencies are inserted above this marker by the template\n"


def _requirement_pattern(package: str) -> str:
    """Match a whole requirement line for `package`, whatever its extras/version."""
    return rf'^[ \t]*"{re.escape(package)}(\[[^\]]*\])?[^"\n]*",[ \t]*\n'


def add_dependency(patcher: FilePatcher, requirement: str, *, dev: bool = False) -> None:
    """Insert `requirement` just above the marker, once."""
    marker = DEV_DEPENDENCY_MARKER if dev else DEPENDENCY_MARKER
    patcher.ensure_insert_before(
        PYPROJECT,
        marker,
        f'    "{requirement}",\n',
        marker=f'    "{requirement}",',
    )


def add_dependencies(patcher: FilePatcher, *requirements: str, dev: bool = False) -> None:
    for requirement in requirements:
        add_dependency(patcher, requirement, dev=dev)


def remove_dependency(patcher: FilePatcher, package: str) -> None:
    """Drop `package` from the dependency list if present, ignoring its pin."""
    patcher.ensure_regex_replace(
        PYPROJECT,
        _requirement_pattern(package),
        "",
        flags=re.MULTILINE,
        on_missing="skip",
    )


def remove_dependencies(patcher: FilePatcher, *packages: str) -> None:
    for package in packages:
        remove_dependency(patcher, package)
