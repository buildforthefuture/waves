#!/usr/bin/env python3
"""Verify dependency licenses against the allowed set.

Covers requirements files, pyproject dependency lists, and the license
file each project must carry. Packages must be mapped in license-db.yaml
before they are used; unmapped or non-permissive dependencies fail.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402

REQ_SPECIFIER = re.compile(r"[=<>!~\[;\s]")
DEPS_START = re.compile(r"^dependencies\s*=\s*\[$")
DEP_ENTRY = re.compile(r"^['\"]([^'\"<>=!~\s]+)")


def parse_requirements(text: str) -> list[str]:
    names: list[str] = []
    for line in text.splitlines():
        entry = line.split("#", 1)[0].strip()
        if not entry or entry.startswith(("-", "--")):
            continue
        name = REQ_SPECIFIER.split(entry, 1)[0]
        if name:
            names.append(name)
    return names


def parse_pyproject(text: str) -> list[str]:
    names: list[str] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if DEPS_START.match(stripped):
            in_deps = True
            continue
        if in_deps:
            if stripped.startswith("]"):
                in_deps = False
                continue
            match = DEP_ENTRY.match(stripped)
            if match:
                names.append(match.group(1))
    return names


def license_signature(text: str) -> str | None:
    if "MIT License" in text and "Permission is hereby granted, free of charge" in text:
        return "MIT"
    if "Apache License" in text and "Version 2.0" in text:
        return "Apache-2.0"
    return None


def check_names(names: list[str], where: str, packages: dict, allowed: set[str]) -> list[str]:
    findings: list[str] = []
    for name in names:
        license_name = packages.get(name)
        if license_name is None:
            findings.append(f"{where}: {name} is not mapped in license-db.yaml")
        elif license_name not in allowed:
            findings.append(f"{where}: {name} is {license_name}, outside the allowed set")
    return findings


def run(root: Path) -> list[str]:
    db = _common.load_yaml(_common.TOOLS_DIR / "license-db.yaml") or {}
    allowed = set(db.get("allowed", []))
    packages = db.get("packages", {})

    findings: list[str] = []
    for requirements in sorted((root / "tools").glob("requirements*.txt")):
        names = parse_requirements(requirements.read_text(encoding="utf-8"))
        findings.extend(check_names(names, requirements.relative_to(root).as_posix(), packages, allowed))

    base = root / "projects"
    for manifest in sorted(base.glob("*/*/*/project.json")) if base.exists() else []:
        pdir = manifest.parent
        rel = pdir.relative_to(root).as_posix()
        for requirements in sorted(pdir.glob("requirements*.txt")):
            names = parse_requirements(requirements.read_text(encoding="utf-8"))
            findings.extend(check_names(names, f"{rel}/{requirements.name}", packages, allowed))
        pyproject = pdir / "pyproject.toml"
        if pyproject.is_file():
            names = parse_pyproject(pyproject.read_text(encoding="utf-8"))
            findings.extend(check_names(names, f"{rel}/pyproject.toml", packages, allowed))
        license_file = pdir / "LICENSE"
        if license_file.is_file():
            signature = license_signature(license_file.read_text(encoding="utf-8", errors="replace"))
            if signature is None:
                findings.append(f"{rel}/LICENSE: not an MIT or Apache-2.0 license text")
            elif signature not in allowed:
                findings.append(f"{rel}/LICENSE: {signature} is outside the allowed set")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    findings = run(Path(args.root).resolve())
    return _common.report(
        f"license check: {len(findings)} finding(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
