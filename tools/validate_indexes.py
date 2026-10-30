#!/usr/bin/env python3
"""Cross-check projects, manifests, specifications, and the catalog.

Verifies that every project follows the required layout, that manifests
and specifications match their schemas and each other, that the catalog
index is complete and sorted, and that project size stays within
limits. With --tags, also verifies each project's release tag.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402
import schema_validator  # noqa: E402

REQUIRED_FILES = [
    "README.md",
    "SPEC.md",
    "spec.yaml",
    "IMPLEMENTATION.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "CHANGELOG.md",
    "SECURITY.md",
    "project.json",
    "docs/architecture.md",
    ".github/workflows/ci.yml",
]
REQUIRED_DIRS = ["src", "tests", "examples"]
MAX_PROJECT_BYTES = 5 * 1024 * 1024
MARKER = "rebuilt from catalog/index.jsonl"


def project_dirs(root: Path) -> list[Path]:
    base = root / "projects"
    if not base.exists():
        return []
    return sorted(p.parent for p in base.glob("*/*/*/project.json"))


def load_schemas() -> tuple[dict, dict]:
    project = _common.load_yaml(_common.TOOLS_DIR / "schemas" / "project.schema.json")
    spec = _common.load_yaml(_common.TOOLS_DIR / "schemas" / "spec.schema.json")
    return project, spec


def validate_project(root: Path, pdir: Path, schemas, domain_names: set[str]):
    findings: list[str] = []
    rel = pdir.relative_to(root).as_posix()
    project_schema, spec_schema = schemas
    try:
        manifest = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{rel}: unreadable project.json ({exc})"], None

    for error in schema_validator.validate(manifest, project_schema):
        findings.append(f"{rel}/project.json: {error}")

    if pdir.name != f"{manifest.get('slug')}-{manifest.get('id')}":
        findings.append(
            f"{rel}: directory name does not match slug-id"
            f" ({manifest.get('slug')}-{manifest.get('id')})"
        )
    parts = pdir.relative_to(root / "projects").parts
    if len(parts) == 3:
        created = manifest.get("created_at", "")
        if parts[0] != created[:4] or parts[1] != created[5:7]:
            findings.append(f"{rel}: year/month shard does not match created_at")
    if manifest.get("domain") not in domain_names:
        findings.append(f"{rel}: domain not present in registry/domains.yaml")

    for name in REQUIRED_FILES:
        if not (pdir / name).is_file():
            findings.append(f"{rel}: missing required file {name}")
    for name in REQUIRED_DIRS:
        target = pdir / name
        if not target.is_dir() or not any(target.iterdir()):
            findings.append(f"{rel}: missing or empty required directory {name}/")
    if not any((pdir / "docs" / "adr").glob("*.md")):
        findings.append(f"{rel}: no architecture decision record under docs/adr/")

    spec_path = pdir / "spec.yaml"
    if spec_path.is_file():
        try:
            spec = _common.load_yaml(spec_path)
        except (OSError, ValueError) as exc:
            findings.append(f"{rel}/spec.yaml: unreadable ({exc})")
            spec = None
        if spec is not None:
            for error in schema_validator.validate(spec, spec_schema):
                findings.append(f"{rel}/spec.yaml: {error}")
            if spec.get("title") != manifest.get("title"):
                findings.append(f"{rel}: spec title differs from manifest title")
            if spec.get("slug") != manifest.get("slug"):
                findings.append(f"{rel}: spec slug differs from manifest slug")
            if spec.get("domain") != manifest.get("domain"):
                findings.append(f"{rel}: spec domain differs from manifest domain")
            if set(spec.get("tags", [])) != set(manifest.get("tags", [])):
                findings.append(f"{rel}: spec tags differ from manifest tags")

    total = sum(f.stat().st_size for f in pdir.rglob("*") if f.is_file())
    if total > MAX_PROJECT_BYTES:
        findings.append(f"{rel}: {total} bytes exceeds the 5 MB project cap")
    return findings, manifest


def validate_catalog(root: Path, manifests: list[dict]) -> list[str]:
    findings: list[str] = []
    index_path = root / "catalog" / "index.jsonl"
    if not index_path.is_file():
        return [f"catalog/index.jsonl: missing"]
    entries: list[tuple[int, dict]] = []
    for lineno, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entries.append((lineno, json.loads(line)))
        except ValueError as exc:
            findings.append(f"catalog/index.jsonl:{lineno}: invalid JSON ({exc})")

    seen: dict[str, int] = {}
    for lineno, entry in entries:
        pid = entry.get("id")
        if pid in seen:
            findings.append(
                f"catalog/index.jsonl:{lineno}: duplicate id {pid} (also line {seen[pid]})"
            )
        seen[pid] = lineno

    for manifest in manifests:
        pid = manifest["id"]
        if pid not in seen:
            findings.append(f"catalog: no index line for project {pid}")
            continue
    for pid in seen:
        if pid not in {m["id"] for m in manifests}:
            findings.append(f"catalog: index line {pid} has no project directory")

    order = [(e.get("created_at", ""), e.get("id", "")) for _, e in entries]
    if order != sorted(order):
        findings.append("catalog: index lines are not sorted by created_at, id")

    for name in ("README.md", "CATALOG.md"):
        path = root / name
        if not path.is_file():
            findings.append(f"{name}: missing")
        elif MARKER not in path.read_text(encoding="utf-8"):
            findings.append(f"{name}: rebuild marker missing; run tools/build_indexes.py")
    return findings


def validate_tags(root: Path, manifests: list[dict]) -> list[str]:
    findings: list[str] = []
    try:
        tags = set(_common.git(root, "tag").split())
    except RuntimeError:
        return ["tags: unable to list repository tags"]
    for manifest in manifests:
        expected = f"proj/{manifest['slug']}-{manifest['id']}/v{manifest['version']}"
        if expected not in tags:
            findings.append(f"{manifest['slug']}-{manifest['id']}: missing tag {expected}")
    return findings


def run(root: Path, with_tags: bool) -> list[str]:
    findings: list[str] = []
    schemas = load_schemas()
    registry = _common.load_yaml(root / "registry" / "domains.yaml") or {}
    domain_names = {d["name"] for d in registry.get("domains", [])}

    manifests: list[dict] = []
    for pdir in project_dirs(root):
        project_findings, manifest = validate_project(root, pdir, schemas, domain_names)
        findings.extend(project_findings)
        if manifest is not None:
            manifests.append(manifest)

    findings.extend(validate_catalog(root, manifests))
    if with_tags:
        findings.extend(validate_tags(root, manifests))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--tags", action="store_true", help="also verify release tags")
    args = parser.parse_args(argv)
    findings = run(Path(args.root).resolve(), args.tags)
    return _common.report(
        f"index validation: {len(findings)} finding(s)", findings
    )


if __name__ == "__main__":
    sys.exit(main())
