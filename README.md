# Incubator

<!-- Do not edit manually; rebuilt from catalog/index.jsonl. -->

Small, focused engineering projects. Each one ships a specification, a
working core with tests, and its documentation, indexed for browsing by
domain, tag, and date.

## Catalog

- Total projects: 0
- Domains covered: 0

Browse:

- [CATALOG.md](CATALOG.md) — all projects grouped by domain
- [catalog/by-domain/](catalog/by-domain/) — one page per domain, at most 200 projects per page
- [catalog/by-tag/](catalog/by-tag/) — one page per tag
- [catalog/by-year/](catalog/by-year/) — additions by month
- [catalog/index.jsonl](catalog/index.jsonl) — the machine-readable index

## Domains

No projects yet.

## Recent projects

No projects yet.

## Layout

```
projects/    one directory per project, sharded by year and month
registry/    domain taxonomy, considered ideas, run records
catalog/     index and browsing pages, rebuilt from the manifests
tools/       the checks every change must pass
```

## Adding a project

Each project carries a manifest, a specification with its machine-readable
twin, a working core with tests, and the standard community files.
`tools/README.md` describes the required layout and the checks to run.
Catalog pages are never edited directly; this script rewrites them from
the manifests.

