"""Release hygiene checks (used by `make check-release`).

Fails when: a junk file is tracked (caches, .env, .venv, out/, backup
bundles, egg-info), a tracked file exceeds 1MB, or a Markdown relative
link does not resolve. Secret scanning is best-effort (grep patterns);
gitleaks/detect-secrets are used when present.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

JUNK_PREFIXES = (
    "__pycache__/", ".mypy_cache/", ".pytest_cache/", ".ruff_cache/", ".hypothesis/",
    ".venv/", "out/", "findings", "htmlcov/", "dist/", "build/", ".env",
    ".coverage", "benchfull/",
)

JUNK_SUFFIXES = (".pyc", ".pyo", ".egg-info", ".bak", ".orig", ".log", ".jsonl",
                 ".bundle", ".DS_Store", "~")


def tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=ROOT
    ).stdout
    return [line for line in out.splitlines() if line]


def check_junk(files: list[str]) -> list[str]:
    problems = []
    for f in files:
        if any(f.startswith(p) for p in JUNK_PREFIXES):
            problems.append(f"junk tracked: {f}")
        if any(f.endswith(s) for s in JUNK_SUFFIXES):
            problems.append(f"junk tracked: {f}")
        if not (ROOT / f).exists():
            continue
        size = (ROOT / f).stat().st_size
        if size > 1_000_000:
            problems.append(f"large file ({size} bytes): {f}")
    return problems


def check_links() -> list[str]:
    problems = []
    for md in list(ROOT.glob("*.md")) + list(ROOT.glob("docs/*.md")):
        text = md.read_text()
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            target = target.split("#")[0]
            if not target:
                continue
            resolved = (md.parent / target).resolve()
            if not resolved.exists():
                problems.append(f"broken link in {md.relative_to(ROOT)}: {target}")
    return problems


SECRET_ALLOWLIST = {("tests/unit/test_rules.py"): ["AKIA[0-9A-Z]{16}"],
                   ("scripts/check_release.py"): None}
# None means: skip this file entirely (its pattern list self-matches).


def check_secrets(files: list[str]) -> list[str]:
    problems = []
    patterns = [
        r"ghp_[A-Za-z0-9]{20,}", r"sk-[A-Za-z0-9]{20,}",
        r"AKIA[0-9A-Z]{16}", r"/home/codespace", "BEGIN " + ".*PRIVATE KEY",
    ]
    for f in files:
        p = ROOT / f
        if p.suffix in (".parquet", ".bundle") or not p.exists():
            continue
        try:
            text = p.read_text(errors="ignore")
        except UnicodeDecodeError:
            continue
        if f in SECRET_ALLOWLIST:
            allowed = SECRET_ALLOWLIST[f]
            if allowed is None:
                continue
            patterns2 = [p for p in patterns if p not in allowed]
        else:
            patterns2 = patterns
        for pat in patterns2:
            if re.search(pat, text):
                problems.append(f"secret-like pattern {pat!r} in {f}")
    return problems


def main() -> None:
    files = tracked()
    problems = check_junk(files) + check_links() + check_secrets(files)
    tool = shutil.which("gitleaks") or shutil.which("detect-secrets")
    if tool:
        print(f"note: {tool} is available; running repo scan")
        proc = subprocess.run([tool, "protect", "--verbose"], cwd=ROOT, capture_output=True)
        if proc.returncode not in (0,):
            problems.append("external secret scanner (gitleaks/detect-secrets) flagged the tree")
    else:
        print("note: no gitleaks/detect-secrets installed; grep-based scan only")
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        raise SystemExit(1)
    print("check-release: OK (junk/link/secret-size checks pass)")


if __name__ == "__main__":
    main()
