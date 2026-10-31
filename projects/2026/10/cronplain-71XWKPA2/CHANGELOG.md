# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog; versions follow Semantic Versioning.

## [0.1.0] - 2026-10-31

### Added

- Five-field cron grammar: lists, ranges, steps, wildcards, month and
  weekday names, and precise per-field validation errors.
- The seven time-based aliases with a clear rejection of `@reboot`.
- Vixie day-field semantics: either-or when both day fields are restricted,
  intersection when a field starts with an asterisk.
- Next and previous run computation with day-level jumps, fast across
  multi-year gaps, and a dedicated error for schedules that never match.
- Deterministic plain-English descriptions.
- Command-line interface with `describe`, `validate`, `next`, and `prev`.
