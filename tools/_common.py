"""Shared helpers for the check scripts in this directory."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

OK = 0
FINDINGS = 1
USAGE = 2

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
}

MAX_SCAN_BYTES = 2_000_000

TOOLS_DIR = Path(__file__).resolve().parent


def is_binary(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(1024)
    except OSError:
        return True
    return b"\x00" in chunk


def iter_files(root: Path, suffix: str | None = None) -> list[Path]:
    """Sorted repository-relative files, skipping internals and binaries."""
    out: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.suffix == ".pyc":
            continue
        if suffix is not None and path.suffix != suffix:
            continue
        if is_binary(path):
            continue
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
        except OSError:
            continue
        out.append(rel)
    return out


def load_yaml(path: Path):
    import yaml

    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def report(summary: str, findings: list[str]) -> int:
    for line in findings:
        print(f"FAIL {line}")
    print(summary)
    return FINDINGS if findings else OK


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout


def diff_added_lines(repo: Path, base: str) -> dict[str, list[tuple[int, str]]]:
    """Map of changed path to its added lines, with line numbers."""
    out = git(repo, "diff", "--no-color", "-U0", base)
    files: dict[str, list[tuple[int, str]]] = {}
    path: str | None = None
    lineno = 0
    for line in out.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :]
            files.setdefault(path, [])
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            lineno = int(match.group(1)) if match else 0
        elif line.startswith("+") and path is not None:
            files[path].append((lineno, line[1:]))
            lineno += 1
    return files


def commit_messages(repo: Path, rev_range: str) -> list[tuple[str, str]]:
    out = git(repo, "log", "--format=%H%x1f%B%x1e", rev_range)
    result: list[tuple[str, str]] = []
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        hash_, _, message = chunk.strip("\n").partition("\x1f")
        result.append((hash_.strip(), message.strip()))
    return result
