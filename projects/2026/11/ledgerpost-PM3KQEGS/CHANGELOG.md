# Changelog

All notable changes to this project are listed here. The format follows Keep a Changelog; versions
are semantic.

## 0.1.0 - 2026-11-01

### Added

- `Money`: immutable integer minor-unit amounts with exact arithmetic, ordering, and lossless
  allocation by integer ratios
- `Posting`, `Transaction`, `Outcome`: validated, frozen value objects with per-currency balance
  enforcement at construction
- `PostingEngine.post`: atomic claim of a request key followed by at-most-once application to the
  ledger
- `IdempotencyStore` protocol with a thread-safe in-memory reference implementation
- `Ledger`: apply-order log, per-account and per-currency balances, per-currency trial balance
- Typed error family under `LedgerpostError`
- Integration, concurrency, and randomized-balance test suites
