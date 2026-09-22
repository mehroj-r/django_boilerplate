from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MissingMode = Literal["error", "skip"]


class PatchOperationError(RuntimeError):
    pass


def insert_before(text: str, anchor: str, addition: str) -> str:
    index = text.find(anchor)
    if index == -1:
        raise PatchOperationError(f"Anchor not found: {anchor!r}")
    return text[:index] + addition + text[index:]


def insert_after(text: str, anchor: str, addition: str) -> str:
    index = text.find(anchor)
    if index == -1:
        raise PatchOperationError(f"Anchor not found: {anchor!r}")
    insert_at = index + len(anchor)
    return text[:insert_at] + addition + text[insert_at:]


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise PatchOperationError(f"Text not found for replacement: {old!r}")
    return text.replace(old, new, 1)


def regex_replace_once(text: str, pattern: str, repl: str, *, flags: int = 0) -> str:
    updated, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count == 0:
        raise PatchOperationError(f"Pattern not found for replacement: {pattern!r}")
    return updated


@dataclass(frozen=True)
class OperationRecord:
    op: str
    path: str
    detail: str


class FilePatcher:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.records: list[OperationRecord] = []

    def resolve_path(self, relative_path: str) -> Path:
        path = self.project_root / relative_path
        if not path.exists():
            raise PatchOperationError(f"File not found: {relative_path}")
        return path

    def read_text(self, relative_path: str) -> str:
        return self.resolve_path(relative_path).read_text(encoding="utf-8")

    def write_text(self, relative_path: str, content: str) -> None:
        self.resolve_path(relative_path).write_text(content, encoding="utf-8")

    def create_file(self, relative_path: str, content: str) -> None:
        path = self.project_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._record("create_file", relative_path, f"Created {relative_path}")

    def _record(self, op: str, relative_path: str, detail: str) -> None:
        self.records.append(OperationRecord(op=op, path=relative_path, detail=detail))

    def _handle_missing(self, on_missing: MissingMode, detail: str) -> bool:
        if on_missing == "skip":
            return False
        raise PatchOperationError(detail)

    def ensure_insert_before(
        self,
        relative_path: str,
        anchor: str,
        addition: str,
        *,
        marker: str | None = None,
        on_missing: MissingMode = "error",
    ) -> bool:
        content = self.read_text(relative_path)
        if marker and marker in content:
            return False

        if anchor not in content:
            return self._handle_missing(
                on_missing,
                f"Anchor not found in {relative_path}: {anchor!r}",
            )

        updated = insert_before(content, anchor, addition)
        self.write_text(relative_path, updated)
        self._record("insert_before", relative_path, anchor)
        return True

    def ensure_insert_after(
        self,
        relative_path: str,
        anchor: str,
        addition: str,
        *,
        marker: str | None = None,
        on_missing: MissingMode = "error",
    ) -> bool:
        content = self.read_text(relative_path)
        if marker and marker in content:
            return False

        if anchor not in content:
            return self._handle_missing(
                on_missing,
                f"Anchor not found in {relative_path}: {anchor!r}",
            )

        updated = insert_after(content, anchor, addition)
        self.write_text(relative_path, updated)
        self._record("insert_after", relative_path, anchor)
        return True

    def ensure_replace(
        self,
        relative_path: str,
        old: str,
        new: str,
        *,
        marker: str | None = None,
        on_missing: MissingMode = "error",
    ) -> bool:
        content = self.read_text(relative_path)
        if marker and marker in content:
            return False

        if old not in content:
            return self._handle_missing(
                on_missing,
                f"Text not found in {relative_path}: {old!r}",
            )

        updated = replace_once(content, old, new)
        self.write_text(relative_path, updated)
        self._record("replace", relative_path, old)
        return True

    def ensure_remove(
        self,
        relative_path: str,
        target: str,
        *,
        marker: str | None = None,
        on_missing: MissingMode = "error",
    ) -> bool:
        content = self.read_text(relative_path)
        if marker and marker in content:
            return False

        if target not in content:
            return self._handle_missing(
                on_missing,
                f"Text not found in {relative_path}: {target!r}",
            )

        updated = content.replace(target, "", 1)
        self.write_text(relative_path, updated)
        self._record("remove", relative_path, target)
        return True

    def ensure_regex_replace(
        self,
        relative_path: str,
        pattern: str,
        repl: str,
        *,
        marker: str | None = None,
        on_missing: MissingMode = "error",
        flags: int = 0,
    ) -> bool:
        content = self.read_text(relative_path)
        if marker and marker in content:
            return False

        updated, count = re.subn(pattern, repl, content, count=1, flags=flags)
        if count == 0:
            return self._handle_missing(
                on_missing,
                f"Pattern not found in {relative_path}: {pattern!r}",
            )

        self.write_text(relative_path, updated)
        self._record("regex_replace", relative_path, pattern)
        return True

    def ensure_contains(
        self,
        relative_path: str,
        snippet: str,
        *,
        trailing_newline: bool = True,
    ) -> bool:
        content = self.read_text(relative_path)
        if snippet in content:
            return False

        updated = content
        if updated and not updated.endswith("\n"):
            updated += "\n"
        updated += snippet
        if trailing_newline and not snippet.endswith("\n"):
            updated += "\n"

        self.write_text(relative_path, updated)
        self._record("contains", relative_path, snippet[:80])
        return True
