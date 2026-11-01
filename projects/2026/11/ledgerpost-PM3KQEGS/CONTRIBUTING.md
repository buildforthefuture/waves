# Contributing to Ledgerpost

Thank you for looking at this project. The following keeps reviews fast and the release small.

## Scope

The package is a library, not a service. Changes that fit: the money type, transaction validation,
the posting engine, the store protocol, the query surface, documentation, and tests. Changes that
need discussion first: new storage backends, new public types, and anything that adds a runtime
dependency.

## Ground rules

- Runtime dependencies stay at zero; development tools are pinned in `pyproject.toml`
- Python 3.10+ only, standard library in `src/` without exception
- Every requirement identifier in `SPEC.md` keeps at least one test; add or update tests in the same
  change as behavior
- Public value objects stay frozen; validate at construction so downstream code never re-checks
- Error messages quote the offending value
- Keep the public API surface in `__init__.py` intentional; new exports need a line in `__all__` and
  a docstring mention

## Workflow

1. Open or claim an issue describing the behavior change
2. Branch, implement, and add tests mapped to requirement identifiers
3. Run the checks:

   ```console
   $ ruff check src tests examples
   $ mypy
   $ PYTHONPATH=src python -m unittest discover -s tests -t .
   ```

4. Open a pull request referencing the issue

Commit subjects follow the Conventional Commits style used across the repository, for example
`fix(engine): reject whitespace-only request keys`.

## Reporting problems

Open an issue in this repository's issue tracker with the smallest transaction set that
reproduces the behavior, the interpreter version, and the unexpected outcome. Include no real
account numbers or amounts from production systems.

## License

By contributing, you agree that your contributions are licensed under the MIT license that covers
this project.
