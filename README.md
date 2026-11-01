# Incubator

<!-- Do not edit manually; rebuilt from catalog/index.jsonl. -->

Small, focused engineering projects. Each one ships a specification, a
working core with tests, and its documentation, indexed for browsing by
domain, tag, and date.

## Catalog

- Total projects: 2
- Domains covered: 2
- Latest addition: [Ledgerpost](projects/2026/11/ledgerpost-PM3KQEGS/README.md) (2026-11)

Browse:

- [CATALOG.md](CATALOG.md) — all projects grouped by domain
- [catalog/by-domain/](catalog/by-domain/) — one page per domain, at most 200 projects per page
- [catalog/by-tag/](catalog/by-tag/) — one page per tag
- [catalog/by-year/](catalog/by-year/) — additions by month
- [catalog/index.jsonl](catalog/index.jsonl) — the machine-readable index

## Domains

| Domain | Projects |
| --- | --- |
| [Financial technology infrastructure](catalog/by-domain/fintech-infra.md) | 1 |
| [General software](catalog/by-domain/software.md) | 1 |

## Recent projects

| Project | Domain | Added |
| --- | --- | --- |
| [Ledgerpost](projects/2026/11/ledgerpost-PM3KQEGS/README.md) | fintech-infra | 2026-11 |
| [Cronplain](projects/2026/10/cronplain-71XWKPA2/README.md) | software | 2026-10 |

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

