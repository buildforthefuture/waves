#!/usr/bin/env python3
"""Flag content that must stay out of this repository.

Checks file contents, filenames, commit messages, and tag names against
the patterns in neutrality-terms.yaml: personal details, provenance or
tooling references, environment-specific paths, and internal addresses.
Documented exceptions live in allowlist.yaml.

Modes:
  --root DIR     scan the whole tree (default)
  --diff BASE    scan only lines added relative to BASE
  --commits RNG  scan commit messages in a revision range

Exit status: 0 clean, 1 findings, 2 usage error.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

DEFAULT_TERMS = _common.TOOLS_DIR / "neutrality-terms.yaml"
DEFAULT_ALLOWLIST = _common.TOOLS_DIR / "allowlist.yaml"


def load_terms(path: Path) -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    data = _common.load_yaml(path) or {}
    content = [re.compile(p, re.IGNORECASE) for p in data.get("content_terms", [])]
    for handle in data.get("owner_handles", []) or []:
        content.append(re.compile(re.escape(handle), re.IGNORECASE))
    filenames = [re.compile(p, re.IGNORECASE) for p in data.get("filename_terms", [])]
    return content, filenames


def load_allowlist(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = _common.load_yaml(path) or {}
    return data.get("neutrality", [])


def _matching_entries(rel: str, entries: list[dict]) -> list[dict]:
    return [entry for entry in entries if fnmatch.fnmatch(rel, entry["path"])]


def whole_file_allowed(rel: str, entries: list[dict]) -> bool:
    matching = _matching_entries(rel, entries)
    return any("allow_terms" not in entry for entry in matching)


def permitted_terms(rel: str, entries: list[dict]) -> set[str]:
    permitted: set[str] = set()
    for entry in _matching_entries(rel, entries):
        permitted.update(entry.get("allow_terms", []))
    return permitted


def scan_text(text: str, patterns: list[re.Pattern[str]]) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                excerpt = match.group(0)
                if len(excerpt) > 50:
                    excerpt = excerpt[:50] + "..."
                hits.append((lineno, pattern.pattern, excerpt))
    return hits


def filename_findings(path: str, patterns: list[re.Pattern[str]]) -> list[str]:
    return [p.pattern for p in patterns if p.search(path)]


def _format(where: str, hits) -> list[str]:
    return [f"{where}:{lineno} term '{pattern}' ({excerpt})" for lineno, pattern, excerpt in hits]


def run_root(root: Path, content: list[re.Pattern[str]], filenames: list[re.Pattern[str]], allow: list[dict]) -> list[str]:
    findings: list[str] = []
    for rel in _common.iter_files(root):
        as_posix = rel.as_posix()
        for pattern in filename_findings(as_posix, filenames):
            findings.append(f"{as_posix}:0 filename term '{pattern}'")
        if whole_file_allowed(as_posix, allow):
            continue
        permitted = permitted_terms(as_posix, allow)
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for lineno, pattern, excerpt in scan_text(text, content):
            if pattern in permitted:
                continue
            findings.append(f"{as_posix}:{lineno} term '{pattern}' ({excerpt})")
    return findings


def run_diff(root: Path, base: str, content: list[re.Pattern[str]], filenames: list[re.Pattern[str]], allow: list[dict]) -> list[str]:
    findings: list[str] = []
    try:
        changed = _common.diff_added_lines(root, base)
    except RuntimeError as exc:
        return [f"diff: {exc}"]
    for path, lines in sorted(changed.items()):
        for pattern in filename_findings(path, filenames):
            findings.append(f"{path}:0 filename term '{pattern}'")
        if whole_file_allowed(path, allow):
            continue
        permitted = permitted_terms(path, allow)
        for lineno, line in lines:
            for pattern in content:
                match = pattern.search(line)
                if match and pattern.pattern not in permitted:
                    excerpt = match.group(0)
                    if len(excerpt) > 50:
                        excerpt = excerpt[:50] + "..."
                    findings.append(f"{path}:{lineno} term '{pattern.pattern}' ({excerpt})")
    return findings


def run_commits(root: Path, rev_range: str, content: list[re.Pattern[str]]) -> list[str]:
    findings: list[str] = []
    try:
        messages = _common.commit_messages(root, rev_range)
    except RuntimeError as exc:
        return [f"commits: {exc}"]
    for hash_, message in messages:
        for lineno, pattern, excerpt in scan_text(message, content):
            findings.append(f"commit {hash_[:10]} term '{pattern}' ({excerpt})")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--root", default=".", help="scan the whole tree")
    source.add_argument("--diff", metavar="BASE", help="scan added lines vs BASE")
    source.add_argument("--commits", metavar="RANGE", help="scan commit messages")
    parser.add_argument("--terms", default=str(DEFAULT_TERMS))
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST))
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    content, filenames = load_terms(Path(args.terms))
    allow = load_allowlist(Path(args.allowlist))
    if args.diff:
        findings = run_diff(root, args.diff, content, filenames, allow)
        scope = f"diff vs {args.diff}"
    elif args.commits:
        findings = run_commits(root, args.commits, content)
        scope = f"commits {args.commits}"
    else:
        findings = run_root(root, content, filenames, allow)
        scope = str(root)
    return _common.report(
        f"neutrality scan ({scope}): {len(findings)} finding(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
