#!/usr/bin/env python3
"""Scan files or a diff for credentials and other secrets.

Looks for private key blocks, known token formats, credential
assignments, environment-style filenames, and high-entropy strings.

Modes:
  --root DIR     scan the whole tree (default)
  --diff BASE    scan only lines added relative to BASE
  --commits RNG  scan commit messages in a revision range

Exit status: 0 clean, 1 findings, 2 usage error.
"""

from __future__ import annotations

import argparse
import fnmatch
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd|access[_-]?key)\b"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+=.]{16,}"
        ),
    ),
]
# Path-shaped strings are excluded (they contain separators); raw key
# material is covered by the specific token and assignment patterns.
ENTROPY_CANDIDATE = re.compile(r"[A-Za-z0-9_\-+=.]{32,}")
ENTROPY_THRESHOLD = 4.3
ENV_FILENAME = re.compile(r"(^|/)\.env")


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(text)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def scan_line(line: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for name, pattern in PATTERNS:
        match = pattern.search(line)
        if match:
            hits.append((name, match.group(0)[:40]))
    for match in ENTROPY_CANDIDATE.finditer(line):
        chunk = match.group(0)
        if shannon_entropy(chunk) >= ENTROPY_THRESHOLD:
            hits.append(("high-entropy-string", chunk[:40]))
    return hits


def scan_file_text(text: str) -> dict[int, list[tuple[str, str]]]:
    findings: dict[int, list[tuple[str, str]]] = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        hits = scan_line(line)
        if hits:
            findings[lineno] = hits
    return findings


def whole_file_allowed(rel: str, entries: list[dict]) -> bool:
    return any(
        fnmatch.fnmatch(rel, entry["path"]) and "allow_rules" not in entry
        for entry in entries
    )


def allowed_rules(rel: str, entries: list[dict]) -> list[str]:
    rules: list[str] = []
    for entry in entries:
        if fnmatch.fnmatch(rel, entry["path"]) and "allow_rules" in entry:
            rules.extend(entry["allow_rules"])
    return rules


def load_allowlist(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = _common.load_yaml(path) or {}
    return data.get("secrets", [])


def run_root(root: Path, allow: list[dict]) -> list[str]:
    findings: list[str] = []
    for rel in _common.iter_files(root):
        as_posix = rel.as_posix()
        if ENV_FILENAME.search(as_posix):
            findings.append(f"{as_posix}:0 env-style filename")
        if whole_file_allowed(as_posix, allow):
            continue
        permitted = set(allowed_rules(as_posix, allow))
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for lineno, hits in scan_file_text(text).items():
            for name, excerpt in hits:
                if name in permitted:
                    continue
                findings.append(f"{as_posix}:{lineno} {name} ({excerpt}...)")
    return findings


def run_diff(root: Path, base: str, allow: list[dict]) -> list[str]:
    findings: list[str] = []
    try:
        changed = _common.diff_added_lines(root, base)
    except RuntimeError as exc:
        return [f"diff: {exc}"]
    for path, lines in changed.items():
        if ENV_FILENAME.search(path):
            findings.append(f"{path}:0 env-style filename")
        if whole_file_allowed(path, allow):
            continue
        permitted = set(allowed_rules(path, allow))
        for lineno, line in lines:
            for name, excerpt in scan_line(line):
                if name in permitted:
                    continue
                findings.append(f"{path}:{lineno} {name} ({excerpt}...)")
    return findings


def run_commits(root: Path, rev_range: str, allow: list[dict]) -> list[str]:
    findings: list[str] = []
    try:
        messages = _common.commit_messages(root, rev_range)
    except RuntimeError as exc:
        return [f"commits: {exc}"]
    for hash_, message in messages:
        if whole_file_allowed("", allow):
            break
        for line in message.splitlines():
            for name, excerpt in scan_line(line):
                findings.append(f"commit {hash_[:10]} {name} ({excerpt}...)")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--root", default=".", help="scan the whole tree")
    source.add_argument("--diff", metavar="BASE", help="scan added lines vs BASE")
    source.add_argument("--commits", metavar="RANGE", help="scan commit messages")
    parser.add_argument(
        "--allowlist",
        default=str(_common.TOOLS_DIR / "allowlist.yaml"),
        help="path to the documented exceptions file",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    allow = load_allowlist(Path(args.allowlist))
    if args.diff:
        findings = run_diff(root, args.diff, allow)
        scope = f"diff vs {args.diff}"
    elif args.commits:
        findings = run_commits(root, args.commits, allow)
        scope = f"commits {args.commits}"
    else:
        findings = run_root(root, allow)
        scope = str(root)
    return _common.report(
        f"secret scan ({scope}): {len(findings)} finding(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
