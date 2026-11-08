"""Unified diff parsing. Small, total (never crashes on garbage input)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(?: (.*))?$")


@dataclass(frozen=True)
class FileChange:
    path_old: str = ""
    path_new: str = ""
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    is_new_file: bool = False
    is_deleted: bool = False

    @property
    def path(self) -> str:
        return self.path_new or self.path_old

    @property
    def added_text(self) -> str:
        return "\n".join(self.added)

    @property
    def removed_text(self) -> str:
        return "\n".join(self.removed)


@dataclass(frozen=True)
class Diff:
    files: tuple[FileChange, ...] = ()
    raw: str = ""

    def changed_paths(self) -> list[str]:
        return [f.path for f in self.files]

    def all_added(self) -> str:
        return "\n".join(f.added_text for f in self.files)

    def all_removed(self) -> str:
        return "\n".join(f.removed_text for f in self.files)


def _strip_ab(path: str) -> str:
    path = path.strip()
    if path.startswith(("a/", "b/")):
        return path[2:]
    if path == "/dev/null":
        return ""
    return path


def parse_diff(text: str | None) -> Diff:
    """Parse a unified diff. Non-diff lines are ignored; result is total."""
    if not text:
        return Diff(files=(), raw="")
    raw = text
    files: list[FileChange] = []
    cur_old = ""
    cur_new = ""
    added: list[str] = []
    removed: list[str] = []
    in_hunk = False
    seen_diff = False

    def flush() -> None:
        if seen_diff:
            files.append(
                FileChange(
                    path_old=cur_old,
                    path_new=cur_new,
                    added=tuple(added),
                    removed=tuple(removed),
                    is_new_file=cur_old == "",
                    is_deleted=cur_new == "",
                )
            )

    for line in text.splitlines():
        if line.startswith("diff --git "):
            flush()
            seen_diff = True
            added = []
            removed = []
            in_hunk = False
            parts = line[len("diff --git ") :].strip().split()
            cur_old = _strip_ab(parts[0]) if len(parts) >= 1 else ""
            cur_new = _strip_ab(parts[1]) if len(parts) >= 2 else cur_old
            continue
        if line.startswith("--- "):
            cur_old = _strip_ab(line[4:])
            if cur_old == "":
                pass
            continue
        if line.startswith("+++ "):
            cur_new = _strip_ab(line[4:])
            continue
        if line.startswith("@@"):
            in_hunk = bool(_HUNK_RE.match(line)) or True
            continue
        if not in_hunk and not seen_diff:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    flush()
    return Diff(files=tuple(files), raw=raw)


def is_test_path(path: str) -> bool:
    p = path.lower().replace("\\", "/")
    base = p.rsplit("/", 1)[-1]
    return (
        p.startswith("tests/")
        or "/tests/" in p
        or base in {"conftest.py", "pytest.ini", "tox.ini", "setup.cfg"}
        or p.startswith(".github/workflows/")
        or p.startswith(".github/")
        or base.startswith("test_")
        or base.endswith("_test.py")
    )
