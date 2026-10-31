# Specification

Cronplain parses, validates, describes, and iterates standard five-field cron
expressions. The machine-readable twin of this document is `spec.yaml`.

## Problem

Cron expressions appear in job runners, CI platforms, and cloud schedulers,
yet they remain hard to read and easy to get wrong. The existing Python
options split the work: scheduling runners compute times without explaining
them, description libraries carry dependencies and cannot compute runs, and
shell validators give terse errors that hide which field is wrong.

## Users

- Developers embedding cron schedules in applications and dashboards
- Operators reviewing crontabs and scheduler configuration
- Authors of CI and deployment tooling that accepts schedule input

## Goals

1. Parse standard five-field expressions with lists, ranges, steps, names,
   and aliases.
2. Explain any accepted schedule as deterministic plain English.
3. Compute next and previous runs over the wall-clock calendar.
4. Report precisely which field is wrong and why.
5. Run anywhere Python runs, with no third-party runtime packages.

## Non-goals

- Quartz-style six-field and year-field expressions
- Timezone conversion or daylight-saving-aware scheduling
- The `@reboot` alias and per-user crontab file handling
- Localization of descriptions beyond English

## Requirements

Priorities follow MoSCoW. Every MUST requirement has at least one passing
test that names its identifier.

### FR-1 Field grammar (MUST)

Parse standard five-field expressions using lists, ranges, steps, wildcards,
numeric values, and three-letter month and weekday names.

- Acceptance: `*/15 0,12 1-7 JAN *` parses to the expected minute, hour,
  day, and month values.
- Acceptance: each parsed field exposes its sorted value set for inspection.

### FR-2 Time-based aliases (MUST)

Support the seven time-based `@` aliases and reject `@reboot` with a clear
explanation.

- Acceptance: `@yearly`, `@annually`, `@monthly`, `@weekly`, `@daily`,
  `@midnight`, and `@hourly` expand to their standard equivalents.
- Acceptance: `@reboot` is rejected with a message explaining it is not
  time-based.

### FR-3 Precise validation errors (MUST)

Reject malformed or out-of-range fields with an error that names the field
and the offending input.

- Acceptance: minute 60, weekday 8, and month `FOO` each produce an error
  naming the field.
- Acceptance: expressions with the wrong number of fields are rejected with
  guidance.

### FR-4 Weekday normalization (MUST)

Treat 0 and 7 in the weekday field as Sunday and accept three-letter names
case-insensitively.

- Acceptance: `0 0 * * 0` and `0 0 * * 7` produce identical schedules.
- Acceptance: `0 0 * * sun` matches the same times as `0 0 * * 0`.

### FR-5 Day selection rule (MUST)

Apply the standard rule for combining day-of-month and day-of-week: either
field may decide the day when both are restricted, and a field that starts
with an asterisk intersects with the other.

- Acceptance: `0 0 1 * 1` fires on the 1st of the month or on any Monday.
- Acceptance: `0 0 */5 * 1` fires only on Mondays that are also every 5th
  day of the month.
- Acceptance: `0 0 * * 1` fires only on Mondays when day-of-month is
  unrestricted.

### FR-6 Next-run computation (MUST)

Compute the next matching wall-clock time strictly after a given naive
datetime, skipping dates the calendar does not have, and fail clearly for
schedules that can never match.

- Acceptance: `0 0 31 * *` from the start of February returns the last day
  of March.
- Acceptance: `0 0 29 2 *` matches the next leap years, and `0 0 31 2 *`
  reports that the schedule never matches.

### FR-7 Previous-run computation (MUST)

Compute the previous matching wall-clock time strictly before a given naive
datetime, with the same calendar handling in reverse.

- Acceptance: `@hourly` before 14:30:30 returns 14:00, and before exactly
  14:00 returns 13:00.
- Acceptance: `0 0 1 * *` before the 1st returns the 1st of the previous
  month.

### FR-8 Plain-English description (MUST)

Produce a deterministic plain-English description of any accepted
expression, stating the either-or day rule explicitly when it applies.

- Acceptance: `*/15 * * * *` describes as "Every 15 minutes".
- Acceptance: `0 9 * * 1-5` mentions 09:00 and Monday through Friday.
- Acceptance: `0 0 1 * 1` states that the 1st of the month or a Monday both
  qualify.

### FR-9 Command-line interface (MUST)

Expose `describe`, `validate`, `next`, and `prev` subcommands with non-zero
exit status for invalid input.

- Acceptance: `next` with a count prints that many ISO timestamps.
- Acceptance: an invalid expression exits with status 1 and an error on
  standard error.

### NFR-1 Zero runtime dependencies (MUST)

Run on the Python standard library alone.

- Acceptance: the package imports and its whole suite passes on a clean
  interpreter.

### NFR-2 Safe parsing (MUST)

Parsing untrusted input only ever raises the library error type, never an
unrelated exception, and never recurses or loops unboundedly.

- Acceptance: a corpus of malformed strings raises only the library error
  type.

### NFR-3 Responsive computation (SHOULD)

Answer parse and next-run queries quickly, including schedules whose matches
are years apart.

- Acceptance: one thousand parses complete in under a second.
- Acceptance: the next February 29 across an eight-year span resolves in
  under a second.

## Test strategy

Unit tests cover field grammar, alias expansion, day selection, and every
documented error path. Iteration tests assert exact next and previous
datetimes around month lengths, leap years, weekends, and the either-or day
rule, plus termination for schedules that never match. Description tests pin
golden strings, and CLI tests drive the entry point in process while
checking exit codes.

## Security notes

Parsing accepts untrusted strings: input is never evaluated, all malformed
shapes surface as the library error type, and iteration is bounded so no
expression can cause unbounded work. The command-line interface reads only
its arguments and prints only computed text.

## Roadmap

1. Optional six-field Quartz-style expressions with a year field
2. Optional timezone-aware iteration built on `zoneinfo`
3. Localization hooks for descriptions
4. Whole-line crontab file parsing

## Technology

| Area | Choice | Rationale |
| --- | --- | --- |
| Language | Python 3.10+ | Ubiquitous where cron strings are configured |
| Runtime dependencies | None | Short audits, simple supply chain |
| Build | setuptools via pyproject.toml | Standard, low-ceremony packaging |
| Tests | unittest | In the standard library, zero setup |
| Lint | ruff | Fast, covers style and correctness rules |
| Type check | mypy, strict | Catches shape bugs in a pure core |
