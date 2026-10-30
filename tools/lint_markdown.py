#!/usr/bin/env python3
"""Structural markdown rules for every markdown file in the tree.

Rules:
  md01  exactly one top-level heading, and it comes first
  md02  heading levels increase by at most one step
  md03  trailing whitespace
  md04  hard tabs
  md05  line longer than 160 characters (table rows: 300)
  md06  fenced code block left open
  md07  leftover TODO or FIXME marker
  md08  file does not end with a newline
  md09  three or more consecutive blank lines
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

FENCE = re.compile(r"^\s*(?:```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s")
MARKER = re.compile(r"\b(?:TODO|FIXME)\b")
PROSE_LIMIT = 160
TABLE_LIMIT = 300


def lint_text(text: str) -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    lines = text.splitlines()
    in_fence = False
    h1_count = 0
    first_heading_seen = False
    last_level = 0
    blank_run = 0

    for lineno, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            blank_run = 0
            continue
        if in_fence:
            continue
        if not line.strip():
            blank_run += 1
            if blank_run >= 3:
                findings.append(("md09", lineno, "three or more blank lines"))
            continue
        blank_run = 0

        if HEADING.match(line):
            level = len(line) - len(line.lstrip("#"))
            if level == 1:
                h1_count += 1
                if not first_heading_seen:
                    first_heading_seen = True
            elif not first_heading_seen:
                findings.append(("md01", lineno, "first heading is not top-level"))
                first_heading_seen = True
            if last_level and level > last_level + 1:
                findings.append(
                    ("md02", lineno, f"heading jumps from h{last_level} to h{level}")
                )
            last_level = level

        if line != line.rstrip():
            findings.append(("md03", lineno, "trailing whitespace"))
        if "\t" in line:
            findings.append(("md04", lineno, "hard tab"))
        limit = TABLE_LIMIT if line.lstrip().startswith("|") else PROSE_LIMIT
        if len(line) > limit:
            findings.append(("md05", lineno, f"line longer than {limit} characters"))
        if MARKER.search(line):
            findings.append(("md07", lineno, "leftover TODO/FIXME marker"))

    if in_fence:
        findings.append(("md06", len(lines), "fenced code block left open"))
    if h1_count != 1:
        findings.append(("md01", 0, f"{h1_count} top-level headings, expected 1"))
    if text and not text.endswith("\n"):
        findings.append(("md08", len(lines), "file does not end with a newline"))
    return findings


def run(root: Path) -> list[str]:
    findings: list[str] = []
    for rel in _common.iter_files(root, suffix=".md"):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for rule, lineno, detail in lint_text(text):
            findings.append(f"{rel.as_posix()}:{lineno} {rule} {detail}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    findings = run(Path(args.root).resolve())
    return _common.report(
        f"markdown lint: {len(findings)} finding(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
