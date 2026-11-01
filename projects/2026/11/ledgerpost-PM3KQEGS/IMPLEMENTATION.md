# Implementation Guide

Build order, module map, and conventions for Ledgerpost. The specification in `SPEC.md` is
authoritative; this document describes how the code is arranged and why.

## Build order

1. `errors.py` — the exception family; everything else raises from here
2. `money.py` — the `Money` value object with exact integer arithmetic
3. `model.py` — `Direction`, `Posting`, `Transaction`, `Outcome`; construction-time validation
4. `store.py` — the `IdempotencyStore` protocol and the thread-safe reference store
5. `ledger.py` — append-only log plus running balances and the trial balance
6. `engine.py` — the claim-then-apply posting flow
7. Tests per module, then integration and concurrency suites
8. Examples and documentation last, against the finished interface

## Module map

| Module | Responsibility | Key types |
| --- | --- | --- |
| `src/ledgerpost/errors.py` | Typed exception family | `LedgerpostError` base |
| `src/ledgerpost/money.py` | Minor-unit amounts, allocation | `Money` |
| `src/ledgerpost/model.py` | Value objects and validation | `Direction`, `Posting`, `Transaction`, `Outcome` |
| `src/ledgerpost/store.py` | Claim protocol + reference store | `IdempotencyStore`, `MemoryIdempotencyStore` |
| `src/ledgerpost/ledger.py` | Log, balances, trial balance | `Ledger` |
| `src/ledgerpost/engine.py` | Claim-then-apply flow | `PostingEngine` |

Dependency direction is strictly downward: `engine` needs `store`, `ledger`, `model`; `ledger`
needs `model`; `model` needs `money`; `money` needs `errors`. No cycles, no upward imports.

## Conventions

- Public API lives in `__init__.py`; modules are importable but the flat surface is the contract
- Every value object is a frozen dataclass with slots; mutation is impossible by construction
- Amounts are `int` minor units; `bool` is rejected explicitly because it subclasses `int`
- Construction-time validation only: an accepted object is always valid, so the engine and ledger
  never re-check
- No wall clock, no randomness, no global state; identifiers come from callers
- Locks protect mutation (`MemoryIdempotencyStore`, `Ledger`); the engine itself is lock-free
  because the store's atomic claim serializes the winner
- Error messages quote the offending value; no bare error codes

## Definition of done

- Every MUST and SHOULD requirement in `SPEC.md` has at least one passing test named for it
- `ruff check src tests examples` reports nothing
- `mypy` in strict mode reports nothing
- The full unittest suite passes on Python 3.10+
- The example in `examples/` runs and prints the documented output
- No third-party runtime imports appear anywhere under `src/`
