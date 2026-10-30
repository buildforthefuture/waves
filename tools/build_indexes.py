#!/usr/bin/env python3
"""Rebuild every catalog file from the project manifests.

Reads projects/*/*/*/project.json, validates each against
schemas/project.schema.json, and rewrites catalog/index.jsonl, the
by-domain, by-tag, and by-year pages, CATALOG.md, and README.md.
The output is deterministic: the same manifests always produce the same
bytes. Catalog files are owned by this script; never edit them by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common  # noqa: E402
import schema_validator  # noqa: E402

TITLE = "Incubator"
INTRO = [
    "Small, focused engineering projects. Each one ships a specification, a",
    "working core with tests, and its documentation, indexed for browsing by",
    "domain, tag, and date.",
]
PAGE_SIZE = 200
SUMMARY_CELL_LIMIT = 80
MARKER = "<!-- Do not edit manually; rebuilt from catalog/index.jsonl. -->"


def load_manifests(root: Path) -> list[dict]:
    schema = _common.load_yaml(_common.TOOLS_DIR / "schemas" / "project.schema.json")
    projects: list[dict] = []
    for manifest in sorted((root / "projects").glob("*/*/*/project.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        errors = schema_validator.validate(data, schema)
        if errors:
            raise SystemExit(
                f"invalid manifest {manifest}: " + "; ".join(errors)
            )
        data["path"] = manifest.parent.relative_to(root).as_posix()
        projects.append(data)
    projects.sort(key=lambda p: (p["created_at"], p["id"]))
    return projects


def domain_displays(root: Path) -> dict[str, str]:
    data = _common.load_yaml(root / "registry" / "domains.yaml") or {}
    return {d["name"]: d.get("display", d["name"]) for d in data.get("domains", [])}


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def row_for(project: dict, include_tags: bool) -> str:
    title = f"[{project['title']}](../../{project['path']}/README.md)"
    cells = [title, truncate(project["summary"], SUMMARY_CELL_LIMIT)]
    if include_tags:
        cells.append(", ".join(project["tags"]))
    cells.append(project["created_at"][:7])
    return "| " + " | ".join(cells) + " |"


def page_names(base: str, count: int) -> list[str]:
    if count <= 1:
        return [f"{base}.md"]
    return [f"{base}.md"] + [f"{base}-{n}.md" for n in range(2, count + 1)]


def write_pages(
    root: Path, subdir: str, groups: dict[str, tuple[str, list[dict], bool]]
) -> None:
    """Write one group of pages; each group holds at most PAGE_SIZE rows a page."""
    directory = root / "catalog" / subdir
    directory.mkdir(parents=True, exist_ok=True)
    expected: set[str] = set()
    for base in sorted(groups):
        heading, rows, include_tags = groups[base]
        chunks = [rows[i : i + PAGE_SIZE] for i in range(0, len(rows), PAGE_SIZE)]
        names = page_names(base, len(chunks))
        expected.update(names)
        for index, (name, chunk) in enumerate(zip(names, chunks), 1):
            page_heading = heading if len(chunks) == 1 else f"{heading} (page {index})"
            lines = [
                f"# {page_heading}",
                "",
                MARKER,
                "",
                f"{len(rows)} project(s).",
                "",
                "| Project | Summary | Tags | Added |" if include_tags else "| Project | Summary | Added |",
                "| --- | --- | --- | --- |" if include_tags else "| --- | --- | --- |",
            ]
            lines.extend(row_for(p, include_tags) for p in chunk)
            (directory / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    sync_directory(directory, expected)


def sync_directory(directory: Path, expected: set[str]) -> None:
    for existing in directory.glob("*.md"):
        if existing.name not in expected:
            existing.unlink()
    keep = directory / ".gitkeep"
    if expected:
        keep.unlink(missing_ok=True)
    else:
        keep.write_text("", encoding="utf-8")


def write_catalog(root: Path, projects: list[dict], displays: dict[str, str]) -> None:
    lines = ["# Catalog", "", MARKER, ""]
    if not projects:
        lines.append("No projects yet.")
    else:
        counts: dict[str, int] = {}
        for project in projects:
            counts[project["domain"]] = counts.get(project["domain"], 0) + 1
        lines.append(
            f"{len(projects)} project(s) across {len(counts)} domain(s)."
        )
        lines += ["", "## By domain", "", "| Domain | Projects |", "| --- | --- |"]
        for domain in sorted(counts, key=lambda d: (-counts[d], d)):
            lines.append(
                f"| [{displays.get(domain, domain)}]"
                f"(catalog/by-domain/{domain}.md) | {counts[domain]} |"
            )
        months: dict[str, int] = {}
        for project in projects:
            month = project["created_at"][:7]
            months[month] = months.get(month, 0) + 1
        lines += ["", "## By month", ""]
        for month in sorted(months, reverse=True):
            lines.append(f"- [{month}](catalog/by-year/{month}.md) ({months[month]})")
    (root / "CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(root: Path, projects: list[dict], displays: dict[str, str]) -> None:
    lines = [f"# {TITLE}", "", MARKER, "", *INTRO, "", "## Catalog", ""]
    lines.append(f"- Total projects: {len(projects)}")
    domains_used = {p["domain"] for p in projects}
    lines.append(f"- Domains covered: {len(domains_used)}")
    if projects:
        latest = projects[-1]
        lines.append(
            f"- Latest addition: [{latest['title']}]({latest['path']}/README.md)"
            f" ({latest['created_at'][:7]})"
        )
    lines += [
        "",
        "Browse:",
        "",
        "- [CATALOG.md](CATALOG.md) — all projects grouped by domain",
        "- [catalog/by-domain/](catalog/by-domain/) — one page per domain, at most 200 projects per page",
        "- [catalog/by-tag/](catalog/by-tag/) — one page per tag",
        "- [catalog/by-year/](catalog/by-year/) — additions by month",
        "- [catalog/index.jsonl](catalog/index.jsonl) — the machine-readable index",
        "",
        "## Domains",
        "",
    ]
    if projects:
        counts: dict[str, int] = {}
        for project in projects:
            counts[project["domain"]] = counts.get(project["domain"], 0) + 1
        lines += ["| Domain | Projects |", "| --- | --- |"]
        for domain in sorted(counts, key=lambda d: (-counts[d], d)):
            lines.append(
                f"| [{displays.get(domain, domain)}](catalog/by-domain/{domain}.md)"
                f" | {counts[domain]} |"
            )
    else:
        lines.append("No projects yet.")
    lines += ["", "## Recent projects", ""]
    if projects:
        lines += ["| Project | Domain | Added |", "| --- | --- | --- |"]
        for project in reversed(projects[-10:]):
            lines.append(
                f"| [{project['title']}]({project['path']}/README.md)"
                f" | {project['domain']} | {project['created_at'][:7]} |"
            )
    else:
        lines.append("No projects yet.")
    lines += [
        "",
        "## Layout",
        "",
        "```",
        "projects/    one directory per project, sharded by year and month",
        "registry/    domain taxonomy, considered ideas, run records",
        "catalog/     index and browsing pages, rebuilt from the manifests",
        "tools/       the checks every change must pass",
        "```",
        "",
        "## Adding a project",
        "",
        "Each project carries a manifest, a specification with its machine-readable",
        "twin, a working core with tests, and the standard community files.",
        "`tools/README.md` describes the required layout and the checks to run.",
        "Catalog pages are never edited directly; this script rewrites them from",
        "the manifests.",
        "",
    ]
    (root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(root: Path) -> list[dict]:
    projects = load_manifests(root)
    displays = domain_displays(root)
    for project in projects:
        if project["domain"] not in displays:
            raise SystemExit(f"unknown domain: {project['domain']}")

    index_lines = [json.dumps(p, sort_keys=True) for p in projects]
    (root / "catalog").mkdir(exist_ok=True)
    (root / "catalog" / "index.jsonl").write_text(
        "".join(line + "\n" for line in index_lines), encoding="utf-8"
    )

    by_domain: dict[str, tuple[str, list[dict], bool]] = {}
    by_tag: dict[str, tuple[str, list[dict], bool]] = {}
    by_year: dict[str, tuple[str, list[dict], bool]] = {}
    for project in projects:
        domain = project["domain"]
        by_domain.setdefault(
            domain, (f"{displays[domain]} projects", [], True)
        )[1].append(project)
        for tag in project["tags"]:
            by_tag.setdefault(tag, (f"Projects tagged {tag}", [], True))[1].append(project)
        month = project["created_at"][:7]
        by_year.setdefault(month, (f"Additions {month}", [], True))[1].append(project)

    write_pages(root, "by-domain", by_domain)
    write_pages(root, "by-tag", by_tag)
    write_pages(root, "by-year", by_year)
    write_catalog(root, projects, displays)
    write_readme(root, projects, displays)
    return projects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    projects = build(root)
    print(f"catalog rebuilt: {len(projects)} project(s)")
    return _common.OK


if __name__ == "__main__":
    sys.exit(main())
