#!/usr/bin/env python3
"""Check markdown links: relative targets must exist, anchors must resolve.

External links are format-checked only, unless --online is given, in
which case each one is fetched with a short timeout.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

FENCE = re.compile(r"^\s*(?:```|~~~)")
INLINE_LINK = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
REF_DEF = re.compile(r"^\s{0,3}\[([^\]]+)\]:\s*(\S+)\s*$")
REF_LINK = re.compile(r"\[([^\]]*)\]\[([^\]]*)\]")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def strip_fences(text: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return lines


def slugify(heading: str) -> str:
    lowered = heading.lower()
    cleaned = "".join(ch if ch.isalnum() or ch in " -" else "" for ch in lowered)
    return cleaned.strip().replace(" ", "-")


def heading_slugs(lines: list[str]) -> set[str]:
    return {slugify(m.group(2)) for line in lines if (m := HEADING.match(line))}


def check_online(url: str) -> str | None:
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=8):
            return None
    except Exception as exc:  # noqa: BLE001 - report any failure
        return str(exc)[:80]


def check_target(root: Path, rel: Path, target: str, online: bool) -> list[str]:
    findings: list[str] = []
    where = rel.as_posix()
    if target.startswith("mailto:"):
        return [f"{where}: mailto link ({target})"]
    if target.startswith(("http://", "https://")):
        if online:
            problem = check_online(target)
            if problem:
                findings.append(f"{where}: unreachable {target} ({problem})")
        return findings
    if target.startswith("#"):
        anchor = slugify(target[1:])
        lines = strip_fences((root / rel).read_text(encoding="utf-8"))
        if anchor and anchor not in heading_slugs(lines):
            findings.append(f"{where}: anchor '{target}' not found")
        return findings

    path_part, _, anchor = target.partition("#")
    resolved = (rel.parent / path_part).as_posix() if path_part else rel.as_posix()
    if path_part and not (root / resolved).exists():
        findings.append(f"{where}: broken link '{target}' (missing {resolved})")
        return findings
    if anchor and resolved.endswith(".md"):
        lines = strip_fences((root / resolved).read_text(encoding="utf-8"))
        slug = slugify(anchor)
        if slug not in heading_slugs(lines):
            findings.append(f"{where}: anchor '{target}' not found in {resolved}")
    return findings


def check_file(root: Path, rel: Path, online: bool) -> list[str]:
    text = (root / rel).read_text(encoding="utf-8")
    visible = strip_fences(text)
    definitions: dict[str, str] = {}
    for line in visible:
        if match := REF_DEF.match(line):
            definitions[match.group(1)] = match.group(2)

    findings: list[str] = []
    for lineno, line in enumerate(visible, 1):
        for match in INLINE_LINK.finditer(line):
            target = match.group(2)
            for problem in check_target(root, rel, target, online):
                findings.append(f"{problem} (line {lineno})")
        for match in REF_LINK.finditer(line):
            ref = match.group(2) or match.group(1)
            target = definitions.get(ref)
            if target is None:
                findings.append(f"{rel.as_posix()}:{lineno} undefined reference '{ref}'")
                continue
            for problem in check_target(root, rel, target, online):
                findings.append(f"{problem} (line {lineno})")
    return findings


def run(root: Path, online: bool) -> list[str]:
    findings: list[str] = []
    for rel in _common.iter_files(root, suffix=".md"):
        findings.extend(check_file(root, rel, online))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--online", action="store_true", help="also fetch external links")
    args = parser.parse_args(argv)
    findings = run(Path(args.root).resolve(), args.online)
    return _common.report(
        f"link check: {len(findings)} finding(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
