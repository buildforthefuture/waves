# Ledgerpost

An embeddable double-entry posting engine that turns at-least-once requests into exactly-once
balanced ledger movements.

## Problem

Payment-adjacent services receive the same business event repeatedly: delivery webhooks retry,
clients resend after timeouts, jobs re-run after crashes. Each repeat must produce one set of ledger
movements, and those movements must balance per currency. Teams glue a hand-rolled dedupe store
beside ledger code and the two drift apart, producing double credits or silent gaps.

## Users

- Backend engineers building wallets, billing, and payment-adjacent services
- Platform teams embedding a small ledger inside a larger service
- Maintainers of accounting integrations that receive retried webhooks

## Goals

- Claim a request key once and apply its transaction at most once
- Return the recorded outcome on every repeated request
- Enforce per-currency debit and credit balance at construction time
- Answer account balances and a per-currency trial balance
- Offer a pluggable idempotency store protocol with a thread-safe in-memory reference
- Run on any Python 3.10+ interpreter with no third-party runtime packages

## Non-goals

- Shipping database-backed store implementations
- HTTP endpoints, webhook receivers, or queue consumers
- Currency conversion or exchange-rate handling
- Report, export, or statement formats
- Distributed transaction coordination across services

## Requirements

### FR-001 Integer minor-unit money (MUST)

Provide an immutable `Money` value carrying an integer count of minor units and a three-letter
uppercase currency code. Reject floats and booleans at construction, support exact addition,
subtraction, integer scaling, ordering, and lossless allocation by integer ratios.

Acceptance:

- Constructing `Money` with a float or bool raises `InvalidAmountError`
- 10 plus 20 minor units equals exactly 30 minor units
- Adding amounts of two currencies raises `CurrencyMismatchError`
- Allocating 5 minor units across three equal ratios yields 2, 2, 1 and sums back to 5

### FR-002 Balanced transactions by construction (MUST)

A `Transaction` holds at least two postings, each an account name, a debit or credit direction,
and a positive `Money` amount. Construction fails unless debit and credit totals match for every
currency in the transaction, so a multi-currency transaction is allowed when each currency
balances on its own.

Acceptance:

- Debit 25.00 against credit 24.00 raises `UnbalancedTransactionError`
- A transaction with fewer than two postings raises `InsufficientPostingsError`
- A transaction balancing USD and EUR independently is accepted
- A currency with credits and no debits raises `UnbalancedTransactionError`

### FR-003 Idempotent posting (MUST)

The engine posts a transaction under a caller-chosen request key. The first call claims the key,
applies the transaction to the ledger, and returns a fresh outcome. Every later call with the same
key applies nothing and returns the recorded transaction flagged as a replay. Concurrent callers
racing on one key observe exactly one fresh outcome.

Acceptance:

- Posting the same key five times appends exactly one transaction
- The replay outcome carries the first transaction, not the new one
- Distinct keys posting equal transactions append two transactions
- Sixteen threads racing one key produce one fresh outcome and fifteen replays

### FR-004 Balances and trial balance (MUST)

The ledger keeps posted transactions in apply order and running per-account, per-currency balances
where debits increase and credits decrease the figure. It answers a single-currency balance, a
full per-currency balance map, and a trial balance that sums every account per currency.

Acceptance:

- After a 2500-unit sale the asset account shows 2500 and the income account -2500
- The trial balance of a ledger fed balanced transactions is zero for every currency
- An unknown account balances to zero rather than raising

### FR-005 Recorded outcome on replay (MUST)

Outcomes are immutable value objects pairing the transaction with a replay flag. The store records
the first accepted outcome; replays return the identical transaction object with the flag set, so
callers see one stable answer per business event.

Acceptance:

- Replay returns a transaction equal to the first outcome's transaction
- Mutating an outcome attribute raises `FrozenInstanceError`
- The replay flag is false exactly once per key

### FR-006 Pluggable idempotency store (SHOULD)

Define a two-method store protocol, `get` and `put_if_absent`, whose implementations must make
claims atomic. Ship a thread-safe in-memory reference implementation and document that durable
backends share the ledger's transaction boundary.

Acceptance:

- The reference store passes the same race tests as the engine
- An alternate store implementation passes the engine test suite unchanged
- The protocol documentation states the atomicity contract

### FR-007 Typed error model (SHOULD)

Raise a family of exceptions under one base class covering money, transaction, and store mistakes,
each with a message naming the offending value so callers can branch on specific cases.

Acceptance:

- Every public error derives from `LedgerpostError`
- Error messages contain the offending value, not a bare code

### FR-008 Account and key hygiene (SHOULD)

Account names, transaction ids, request keys, and metadata entries are bounded in length and
reject empty strings and control characters, keeping hostile delivery payloads from polluting the
ledger.

Acceptance:

- Accounts or keys with control characters raise before any mutation
- Oversized names raise with the limit named in the message

### FR-009 Transaction metadata (COULD)

Transactions may carry a small string-to-string metadata mapping, stored read-only, for
correlation ids and delivery markers.

Acceptance:

- Metadata survives as an immutable mapping copy
- Non-string keys or values raise `InvalidPostingError`

### NFR-001 Deterministic outcomes (MUST)

Core logic reads no wall clock and generates no identifiers; transactions carry caller-assigned
ids, so identical inputs produce identical outcomes on every run.

Acceptance:

- Two runs of the same posting sequence produce equal outcomes
- No module in the package imports time or uuid

### NFR-002 Zero runtime dependencies (MUST)

The package imports only the standard library on Python 3.10 or newer, keeping the dependency
surface of payment paths minimal.

Acceptance:

- Runtime imports are standard library only
- The declared dependency list in pyproject is empty

### NFR-003 Safe under concurrent posting (SHOULD)

One engine instance over one ledger and store handles concurrent threads without lost postings or
duplicate applications.

Acceptance:

- Sixteen threads with distinct keys append sixteen transactions
- The trial balance stays zero after the concurrent runs

### NFR-004 Predictable performance (SHOULD)

Posting and balance queries run in time linear in the postings they touch, and ten thousand
sequential postings complete within a few seconds on commodity hardware.

Acceptance:

- A ten-thousand-posting sequential run finishes inside five seconds

## Stack

| Aspect | Choice |
| --- | --- |
| Language | Python |
| Runtime | CPython 3.10 or newer |
| Runtime libraries | none, standard library only |
| Build | setuptools through pyproject.toml |
| Test | unittest discovery |
| Lint | ruff |
| Type check | mypy in strict mode |

Python was selected over Go and Rust for this release because the core is small, allocation and
arithmetic over integers are exact, and the interpreter's threading model matches the target
deployment style of an embedded library. Dev tools are pinned in `pyproject.toml`.

## Test strategy

Unittest suites per module map every MUST and SHOULD requirement to at least one named test:
construction rejections for money and transactions, engine idempotency including a sixteen-thread
same-key race and a sixteen-thread distinct-key race, ledger balance and trial balance arithmetic,
and an integration suite that replays webhook deliveries out of order with duplicates. A seeded
random loop posts two hundred balanced transactions across three currencies and asserts a zero
trial balance. Lint and strict type checking run alongside tests in continuous integration.

## Security notes

The package performs no network or filesystem input and output and holds no secrets. Hostile
delivery payloads are contained by construction checks: amounts are integers, names and keys are
bounded and reject control characters, and metadata is copied into an immutable mapping. The
engine never logs; visibility decisions stay with the caller. Durability and the exactly-once
guarantee across process restarts depend on the store backend sharing a transaction boundary with
the ledger, which is documented rather than assumed.

## Roadmap

- Reference store and ledger backed by one embedded database in a single transaction boundary
- Snapshot and restore of ledger state for restart-safe deployments
- Optional outbox-style hooks that notify callers after a successful claim
- Statement and export adapters built on the query surface
- Currency metadata table covering ISO 4217 exponents for display formatting
