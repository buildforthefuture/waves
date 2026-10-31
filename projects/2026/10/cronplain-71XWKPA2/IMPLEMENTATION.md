# Implementation notes

## Build order

1. `fields.py` — grammar and errors; the rest of the library depends only on
   its output shape (value set plus star flag per field).
2. `schedule.py` — matching and calendar iteration on top of that shape.
3. `describe.py` — rendering from value sets, deliberately ignorant of the
   original text so equivalent expressions collapse to one description.
4. `cli.py` and `__main__.py` — argument mapping and exit codes.
5. Test suite, grown alongside each module and finalized against the golden
   description strings.

## Module map

| Module | Responsibility |
| --- | --- |
| `cronplain/fields.py` | Field grammar, name tables, alias table, `CronError`/`NoMatchError` |
| `cronplain/schedule.py` | `Schedule`: matching, next/previous runs, day-field rule |
| `cronplain/describe.py` | Deterministic plain-English rendering |
| `cronplain/cli.py` | Subcommands, argument types, exit codes |
| `cronplain/__init__.py` | Public surface: `parse`, `describe`, `Schedule`, errors |

## Conventions

- The library exposes only what the specification promises; everything else
  is module-private with a leading underscore.
- All calendar arithmetic uses naive `datetime` values; no call reads the
  system clock except the CLI's optional default reference moment.
- Errors carry the field name; user-facing text never embeds raw expression
  fragments without quoting them with `repr`.
- Type annotations everywhere; `mypy --strict` passes on `src`.

## Decisions worth knowing

- The star flag is recorded from the raw field text, not derived from the
  value set, because `*/5` and `1-31/5` produce equal sets but different
  day-field behavior under the Vixie rule.
- Backward iteration mirrors forward iteration but returns the *last*
  minute of a jumped month, not the first; getting this wrong lands the
  walk in a disallowed month and loops.
- A twelve-year jump ceiling bounds both directions of the walk; the largest
  real gap between February 29 matches is eight years (century rules make
  2096 to 2104 the worst case), so twelve leaves margin.

## Definition of done

- Every MUST requirement in `SPEC.md` has at least one passing test that
  names it.
- `ruff check`, `mypy --strict`, and the unittest suite all pass cleanly.
- The examples run and the CLI handles the four documented subcommands.
- The package builds with `python -m build` from a clean tree (CI covers
  install and tests; no build artifacts are committed).

## Test coverage map

| Requirement | Tests |
| --- | --- |
| FR-1 | `test_fields.FieldGrammarTest`, `test_matches.MatchingTest` |
| FR-2 | `test_aliases.AliasTest` |
| FR-3 | `test_fields.ValidationErrorsTest` |
| FR-4 | `test_fields.WeekdayNormalizationTest` |
| FR-5 | `test_matches.DayCombinationRuleTest` |
| FR-6 | `test_next.NextRunTest` |
| FR-7 | `test_next.PreviousRunTest`, `test_next.PreviousNeverMatchTest` |
| FR-8 | `test_describe.DescribeTest` |
| FR-9 | `test_cli.CliTest` |
| NFR-1 | declared dependencies are empty; the suite runs with none |
| NFR-2 | `test_fields.SafeParsingTest` |
| NFR-3 | `test_next.PerformanceTest` |
