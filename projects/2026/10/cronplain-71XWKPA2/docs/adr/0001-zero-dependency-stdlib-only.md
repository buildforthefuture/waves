# ADR 0001: Standard library only

- Status: accepted
- Date: 2026-10-31

## Context

Scheduling code tends to sit inside everything from CI jobs to long-running
services, and it is exactly the kind of small, widely embedded dependency
that supply-chain reviews scrutinize. The comparable Python libraries either
compute runs without describing schedules or describe schedules while
pulling runtime dependencies in. Every added package multiplies audit work
for every consumer.

## Decision

Cronplain implements its grammar, calendar walk, and rendering entirely on
the Python standard library. Runtime dependencies are zero; development
tools (ruff, mypy) are optional extras and never imported at runtime.

## Consequences

- Consumers can vendor or audit the whole source in one sitting; there is
  nothing else to review.
- The calendar walk is written by hand instead of reusing a scheduling
  engine, which is why month and leap-year handling carries explicit tests.
- `zoneinfo` from the standard library is available for a future
  timezone-aware layer without changing the dependency policy.
- Packaging stays a plain `pyproject.toml` with an empty `dependencies` list.
