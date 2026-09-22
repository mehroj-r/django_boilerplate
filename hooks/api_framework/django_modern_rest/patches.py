from __future__ import annotations

import re
from pathlib import Path

from patching.deps import add_dependencies, remove_dependencies
from patching.engine import PatchSpec
from patching.ops import FilePatcher

# Packages that only exist to serve the DRF stack.
DRF_ONLY_PACKAGES = (
    "djangorestframework",
    "djangorestframework-simplejwt",
    "drf-spectacular",
    "django-filter",
)


def read_snippet(filename: str) -> str:
    snippets_dir = Path(__file__).resolve().parent / "snippets"
    return (snippets_dir / filename).read_text(encoding="utf-8").rstrip("\n") + "\n"


def replace_file(patcher: FilePatcher, relative_path: str, snippet_file: str) -> None:
    patcher.write_text(relative_path, read_snippet(snippet_file))


def apply_dependencies(patcher: FilePatcher) -> None:
    remove_dependencies(patcher, *DRF_ONLY_PACKAGES)
    add_dependencies(patcher, "django-modern-rest[msgspec,jwt,openapi]>=0.15.0")


def apply_settings(patcher: FilePatcher) -> None:
    patcher.ensure_insert_after(
        "src/config/settings/base.py",
        "from decouple import config\n",
        "from dmr.parsers import JsonParser\nfrom dmr.renderers import JsonRenderer\n",
        marker="from dmr.renderers import JsonRenderer",
    )

    # Swap the DRF app set for dmr's single app.
    patcher.ensure_regex_replace(
        "src/config/settings/base.py",
        r'^ {4}"rest_framework",\n'
        r' {4}"rest_framework_simplejwt",\n'
        r' {4}"rest_framework_simplejwt\.token_blacklist",\n'
        r' {4}"corsheaders",\n'
        r' {4}"django_filters",\n'
        r' {4}"drf_spectacular",\n',
        '    "dmr",\n    "corsheaders",\n',
        marker='    "dmr",',
        flags=re.MULTILINE,
    )

    # SIMPLE_JWT is removed below, and it was the only user of timedelta.
    patcher.ensure_remove(
        "src/config/settings/base.py",
        "from datetime import timedelta\n",
        marker="DMR_SETTINGS = {",
    )

    # REST_FRAMEWORK / SPECTACULAR_SETTINGS / SIMPLE_JWT are DRF-only. Replace
    # the whole span between DEFAULT_AUTO_FIELD and the CORS block so this
    # patch does not depend on the exact contents of those dicts.
    patcher.ensure_regex_replace(
        "src/config/settings/base.py",
        r"REST_FRAMEWORK = \{.*?\n# --- CORS ",
        _dmr_settings_block(),
        marker="DMR_SETTINGS = {",
        flags=re.DOTALL,
    )


def _dmr_settings_block() -> str:
    return (
        "DMR_SETTINGS = {\n"
        '    "parsers": [JsonParser()],\n'
        '    "renderers": [JsonRenderer()],\n'
        '    "validate_responses": True,\n'
        '    "semantic_responses": True,\n'
        '    "global_error_handler": "core.api.exceptions.global_error_handler",\n'
        "}\n"
        "\n"
        'AUTH_USER_MODEL = "account.User"\n'
        "\n"
        "# --- CORS "
    )


def apply_dev_urls(patcher: FilePatcher) -> None:
    """Drop DRF's browsable-API login route, which dmr has no equivalent for."""
    replace_file(patcher, "src/config/urls/dev.py", "config_urls_dev.py")


def apply_full_file_replacements(patcher: FilePatcher) -> None:
    replace_file(patcher, "src/core/api/views.py", "core_api_views.py")
    replace_file(patcher, "src/core/api/exceptions.py", "core_api_exceptions.py")
    replace_file(patcher, "src/core/utils/pagination.py", "core_utils_pagination.py")
    replace_file(patcher, "src/api/v1/core/views/auth.py", "auth_views.py")
    replace_file(patcher, "src/api/v1/core/views/misc.py", "misc_views.py")
    # dmr controllers must be registered through dmr.routing.Router, not plain
    # django.urls.path, or they are invisible to the OpenAPI schema.
    replace_file(patcher, "src/api/v1/core/urls/auth.py", "urls_auth.py")
    replace_file(patcher, "src/api/v1/core/urls/misc.py", "urls_misc.py")
    replace_file(patcher, "src/api/v1/urls.py", "api_v1_urls.py")
    replace_file(patcher, "src/api/url_router.py", "api_url_router.py")
    # drf-spectacular is gone; use dmr's own schema views.
    replace_file(patcher, "src/config/urls/base.py", "config_urls_base.py")
    # The shipped tests assert DRF's response envelope and import
    # rest_framework, neither of which exists here.
    replace_file(patcher, "src/tests/test_health.py", "tests_health.py")
    replace_file(patcher, "src/tests/test_auth.py", "tests_auth.py")
    replace_file(patcher, "src/tests/test_errors.py", "tests_errors.py")


def apply_docs(patcher: FilePatcher) -> None:
    patcher.ensure_replace(
        "README.md",
        "`djangorestframework` + `djangorestframework-simplejwt`",
        "`django-modern-rest` (typed controllers, msgspec serialization)",
        on_missing="skip",
    )


def get_patches() -> list[PatchSpec]:
    return [
        PatchSpec(
            patch_id="api_framework.django_modern_rest.dependencies",
            apply=apply_dependencies,
            priority=10,
        ),
        PatchSpec(
            patch_id="api_framework.django_modern_rest.settings",
            apply=apply_settings,
            priority=20,
        ),
        PatchSpec(
            patch_id="api_framework.django_modern_rest.dev_urls",
            apply=apply_dev_urls,
            priority=30,
        ),
        PatchSpec(
            patch_id="api_framework.django_modern_rest.full_files",
            apply=apply_full_file_replacements,
            priority=40,
        ),
        PatchSpec(
            patch_id="api_framework.django_modern_rest.docs",
            apply=apply_docs,
            priority=50,
        ),
    ]
