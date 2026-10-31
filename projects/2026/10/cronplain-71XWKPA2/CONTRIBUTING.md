# Contributing

Thanks for considering a contribution. The project is small on purpose; the
guidance below keeps it that way.

## Getting started

```sh
pip install -e .[dev]
PYTHONPATH=src python3 -m unittest discover -s tests -t .
ruff check src tests
mypy
```

## Ground rules

- No runtime dependencies. If a change needs one, propose the trade-off in
  an issue first; the default answer is to implement against the standard
  library.
- Public API changes update `SPEC.md`, `spec.yaml`, and the tests together.
- Every bug fix comes with a regression test that fails without the fix.
- Descriptions are golden-tested: if your change alters wording, it must
  update the pinned strings deliberately, never accidentally.
- Keep the diff focused; one logical change per pull request.

## Style

- `ruff check src tests` must pass; line length is 100.
- `mypy --strict` must pass on `src`.
- Type-annotate every function, including tests.
- Commit messages are short, factual, and imperative: "fix: bound backward
  iteration at the calendar floor".

## Reporting problems

Open an issue with the expression, the expected behavior, and the actual
behavior. For anything security-related, see `SECURITY.md`.

## Licensing

By contributing you agree your work is released under the project's MIT
license. Copyright belongs to The Project Authors.
