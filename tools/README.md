# Tools

Every change to `projects/`, `catalog/`, or `registry/` must pass the checks
in this directory before it lands on `main`. Repository CI runs all of them
on every relevant change.

## Checks

| Script | What it does |
| --- | --- |
| `build_indexes.py` | Rebuilds `catalog/index.jsonl`, the by-domain, by-tag, and by-year pages, `CATALOG.md`, and `README.md` from the project manifests. Deterministic: same manifests in, same bytes out. |
| `validate_indexes.py` | Cross-checks projects against the catalog, validates manifests and specifications against the schemas, enforces the required file set and the 5 MB project cap. `--tags` also verifies each project's release tag. |
| `scan_secrets.py` | Looks for credentials: key blocks, known token formats, credential assignments, environment-style filenames, high-entropy strings. `--diff BASE` scans only added lines; `--commits RANGE` scans commit messages. |
| `scan_neutrality.py` | Checks content, filenames, commit messages, and tags against `neutrality-terms.yaml`: no personal details, no provenance or tooling references, no environment-specific paths or internal addresses. |
| `check_links.py` | Verifies that relative links and anchors in markdown resolve. External links are fetched only with `--online`. |
| `lint_markdown.py` | Structural markdown rules: one top-level heading, no level skips, line lengths, balanced fences, no leftover markers. |
| `check_licenses.py` | Verifies dependency licenses against `license-db.yaml` and requires each project to carry an MIT or Apache-2.0 license. |
| `run_project_tests.py` | Runs the test command declared in each project manifest. |
| `schema_validator.py` | Validates a single YAML or JSON file against a schema: `python3 tools/schema_validator.py tools/schemas/spec.schema.json <file>`. |

Exit status is 0 when clean, 1 when there are findings, 2 on usage errors.
Exceptions are documented in `allowlist.yaml`; every entry carries a reason.

## Project layout

A project lives under `projects/<year>/<month>/<slug>-<id>/`, where `<id>` is
the eight-character Crockford base32 suffix of a ULID, and must contain:

```text
README.md            what it is, quickstart, usage
SPEC.md              the specification, readable by humans
spec.yaml            the machine-readable twin of SPEC.md
IMPLEMENTATION.md    build order, module map, conventions, definition of done
CONTRIBUTING.md      how to contribute, generic wording
LICENSE              MIT or Apache-2.0
CHANGELOG.md         release history
SECURITY.md          how to report a problem, generic wording
project.json         manifest: id, slug, title, domain, tags, stack, status,
                     version, created_at, optional commands.test
docs/architecture.md component overview with a diagram
docs/adr/*.md        at least one architecture decision record
src/                 the working core
tests/               tests, each mapped to requirement ids from SPEC.md
examples/            runnable examples
.github/workflows/ci.yml
```

The release tag for a project is `proj/<slug>-<id>/v<version>`.

## Adding a project

1. Create the directory and a valid `project.json`.
2. Write `SPEC.md` and `spec.yaml` and validate the twin:
   `python3 tools/schema_validator.py tools/schemas/spec.schema.json <project>/spec.yaml`.
3. Implement, then test. Every MUST requirement in the specification needs at
   least one passing test, and the test must mention the requirement id.
4. Rebuild the catalog: `python3 tools/build_indexes.py`.
5. Run every check in the table above, then commit the project and the
   rebuilt catalog files as separate commits.

Catalog pages are owned by `build_indexes.py`. Do not edit them by hand.
