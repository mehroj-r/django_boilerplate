"""Unit tests for the patch engine and file operations."""

from __future__ import annotations

import pytest
from patching.deps import DEPENDENCY_MARKER, add_dependency, remove_dependency
from patching.engine import PatchEngine, PatchEngineError, PatchSpec
from patching.ops import FilePatcher, PatchOperationError


def spec(patch_id: str, order: list[str], **kwargs) -> PatchSpec:
    return PatchSpec(patch_id=patch_id, apply=lambda _patcher: order.append(patch_id), **kwargs)


class TestOrdering:
    def test_priority_decides_when_there_are_no_dependencies(self):
        order: list[str] = []
        patches = [spec("c", order, priority=30), spec("a", order, priority=10), spec("b", order, priority=20)]

        assert [p.patch_id for p in PatchEngine.order_patches(patches)] == ["a", "b", "c"]

    def test_after_beats_priority(self):
        order: list[str] = []
        patches = [spec("second", order, priority=1, after=("first",)), spec("first", order, priority=99)]

        assert [p.patch_id for p in PatchEngine.order_patches(patches)] == ["first", "second"]

    def test_unknown_dependency_is_rejected(self):
        order: list[str] = []
        with pytest.raises(PatchEngineError, match="unknown dependency"):
            PatchEngine.order_patches([spec("a", order, after=("ghost",))])

    def test_duplicate_ids_are_rejected(self):
        order: list[str] = []
        with pytest.raises(PatchEngineError, match="Duplicate patch id"):
            PatchEngine.order_patches([spec("a", order), spec("a", order)])

    def test_cycles_are_detected(self):
        order: list[str] = []
        patches = [spec("a", order, after=("b",)), spec("b", order, after=("a",))]

        with pytest.raises(PatchEngineError, match="cyclic"):
            PatchEngine.order_patches(patches)


class TestConflicts:
    def test_conflicting_patches_abort_before_any_apply(self, tmp_path):
        order: list[str] = []
        patches = [spec("a", order, conflicts=("b",)), spec("b", order)]

        with pytest.raises(PatchEngineError, match="conflicts with"):
            PatchEngine(tmp_path).run(patches)

        assert order == []


class TestFilePatcher:
    @pytest.fixture
    def patcher(self, tmp_path):
        (tmp_path / "sample.txt").write_text("alpha\nbeta\ngamma\n")
        return FilePatcher(tmp_path)

    def test_insert_before(self, patcher):
        patcher.ensure_insert_before("sample.txt", "beta\n", "inserted\n")
        assert patcher.read_text("sample.txt") == "alpha\ninserted\nbeta\ngamma\n"

    def test_marker_makes_it_idempotent(self, patcher):
        for _ in range(3):
            patcher.ensure_insert_before("sample.txt", "beta\n", "inserted\n", marker="inserted")

        assert patcher.read_text("sample.txt").count("inserted") == 1

    def test_missing_anchor_raises_by_default(self, patcher):
        with pytest.raises(PatchOperationError, match="Anchor not found"):
            patcher.ensure_insert_before("sample.txt", "nope\n", "x\n")

    def test_missing_anchor_can_be_skipped(self, patcher):
        assert patcher.ensure_insert_before("sample.txt", "nope\n", "x\n", on_missing="skip") is False

    def test_unknown_file_raises(self, patcher):
        with pytest.raises(PatchOperationError, match="File not found"):
            patcher.read_text("missing.txt")


class TestDependencyHelpers:
    """These exist so a version bump in pyproject.toml cannot break generation."""

    @pytest.fixture
    def patcher(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "dependencies = [\n"
            '    "django>=6.1,<7.0",\n'
            '    "djangorestframework>=3.16.0",\n'
            '    "djangorestframework-simplejwt[crypto]>=5.5.1",\n'
            f"{DEPENDENCY_MARKER}"
            "]\n"
        )
        return FilePatcher(tmp_path)

    def test_add_is_idempotent(self, patcher):
        add_dependency(patcher, "celery>=5.4.0")
        add_dependency(patcher, "celery>=5.4.0")

        content = patcher.read_text("pyproject.toml")
        assert content.count('"celery>=5.4.0"') == 1
        assert content.index('"celery>=5.4.0"') < content.index(DEPENDENCY_MARKER.strip())

    def test_remove_ignores_the_pinned_version(self, patcher):
        remove_dependency(patcher, "djangorestframework")

        content = patcher.read_text("pyproject.toml")
        assert "djangorestframework>=3.16.0" not in content
        # Must not also strike the differently-named simplejwt package.
        assert "djangorestframework-simplejwt" in content

    def test_remove_handles_extras(self, patcher):
        remove_dependency(patcher, "djangorestframework-simplejwt")
        assert "simplejwt" not in patcher.read_text("pyproject.toml")

    def test_remove_of_an_absent_package_is_a_no_op(self, patcher):
        before = patcher.read_text("pyproject.toml")
        remove_dependency(patcher, "not-installed")
        assert patcher.read_text("pyproject.toml") == before
