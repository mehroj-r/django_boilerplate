from __future__ import annotations

from patching.deps import add_dependencies
from patching.engine import PatchSpec
from patching.ops import FilePatcher


def read_snippet(filename: str) -> str:
    from pathlib import Path

    SNIPPETS_DIR = Path(__file__).resolve().parent / "snippets"
    return (SNIPPETS_DIR / filename).read_text(encoding="utf-8").rstrip("\n")


def apply_dependencies(patcher: FilePatcher) -> None:
    add_dependencies(patcher, "django-unfold>=0.63.0")


def apply_admin_import(patcher: FilePatcher) -> None:
    """Swap Django's ModelAdmin for unfold's, keeping the import block sorted.

    A straight in-place replacement would leave `unfold` sorted above
    `django_softdelete`, which fails `ruff check` in the generated project.
    """
    patcher.ensure_remove(
        "src/core/admin.py",
        "from django.contrib.admin import ModelAdmin\n",
        marker="from unfold.admin import ModelAdmin",
    )
    patcher.ensure_insert_after(
        "src/core/admin.py",
        "from django_softdelete.filters import SoftDeleteFilter\n",
        "from unfold.admin import ModelAdmin\n",
        marker="from unfold.admin import ModelAdmin",
    )


def apply_settings(patcher: FilePatcher) -> None:
    unfold_apps = read_snippet("unfold_apps.txt")
    unfold_settings = read_snippet("unfold_settings.txt")

    patcher.ensure_replace(
        "src/config/settings/base.py",
        "UNFOLD_APPS = []\n",
        f"{unfold_apps}\n",
        marker="unfold.contrib.filters",
    )

    patcher.ensure_insert_before(
        "src/config/settings/base.py",
        'CORS_URLS_REGEX = r"^/api/.*$"\n',
        f"{unfold_settings}\n\n",
        marker="UNFOLD = {",
    )


def get_patches() -> list[PatchSpec]:
    return [
        PatchSpec(
            patch_id="admin_ui.unfold.dependencies",
            apply=apply_dependencies,
            priority=10,
        ),
        PatchSpec(
            patch_id="admin_ui.unfold.admin_import",
            apply=apply_admin_import,
            priority=20,
        ),
        PatchSpec(
            patch_id="admin_ui.unfold.settings",
            apply=apply_settings,
            priority=30,
        ),
    ]
