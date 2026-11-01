# Ledgerpost

An embeddable double-entry posting engine for Python. It turns at-least-once requests — retried
webhooks, resent clients, re-run jobs — into exactly-once balanced ledger movements, and it does so
with zero third-party runtime dependencies.

## Why

Any service that moves money hears about the same business event more than once. The event source
delivers at least once by design, so "credit the wallet on this callback" is unsafe unless something
remembers the request. Ledgerpost pairs that memory (an idempotency store) with the movement record
(a double-entry ledger) so the answer to "did this event post?" and the posting itself can never
drift apart.

- Transactions are balanced per currency by construction; an unbalanced set of postings cannot exist
- A request key posts at most once; repeats return the recorded outcome flagged as a replay
- Money is integer minor units; floats never touch an amount
- Balances and a per-currency trial balance are one call away

## Quickstart

```python
from ledgerpost import (
    Direction, Ledger, MemoryIdempotencyStore, Money, Posting, PostingEngine, Transaction,
)

ledger = Ledger()
engine = PostingEngine(ledger, MemoryIdempotencyStore())

topup = Transaction(
    "topup-1001",
    [
        Posting("cash:processor", Direction.DEBIT, Money(2500, "USD")),
        Posting("wallet:user-42", Direction.CREDIT, Money(2500, "USD")),
    ],
)

first = engine.post("evt_1001", topup)     # fresh outcome, ledger grows by one
second = engine.post("evt_1001", topup)    # replay: same transaction, nothing applied
print(first.replayed, second.replayed)     # False True
print(ledger.balance("cash:processor", "USD").amount)  # 2500, counted once
```

Install from source:

```console
$ pip install .
```

Requires Python 3.10 or newer. The runtime dependency list is empty.

## Concepts

**Money** is an immutable integer count of minor units plus a three-letter currency code. `10 +
20` minor units is exactly `30`; constructing from a float raises. Allocation across integer
ratios is lossless — five units split three ways lands as two, two, one.

**Posting and Transaction** express double-entry movements. Each posting names an account, a
direction, and a positive amount. A transaction requires at least two postings and rejects itself
unless debit and credit totals match for every currency it touches.

**PostingEngine** is the entry point. `post(request_key, transaction)` claims the key atomically,
applies the transaction at most once, and returns an `Outcome` pairing the transaction with a
replay flag. Give every distinct delivery attempt of one business event the same key.

**IdempotencyStore** is a two-method protocol: `get` and `put_if_absent`. The included
`MemoryIdempotencyStore` is thread-safe and process-local. For durability, implement the protocol
over the same database as the ledger inside one transaction boundary — the architecture notes
explain the contract.

**Ledger** records posted transactions in apply order and answers `balance(account, currency)`, a
per-currency `balance(account)` map, and a per-currency `trial_balance()` that is zero for any
correctly fed ledger.

## Replay semantics

| Call | Ledger effect | Outcome |
| --- | --- | --- |
| First with a key | transaction applied | `replayed=False` |
| Any later call with that key | none | `replayed=True`, recorded transaction |
| Different key, equal transaction | applied again | `replayed=False` |

The replay outcome is the recorded transaction object, not a re-derivation, so callers can rely on
stable values across retries.

## Thread safety

One engine over one ledger and store is safe for concurrent use. Concurrent callers racing on the
same key see exactly one fresh outcome; the winner applies, everyone else replays. Racing on
distinct keys applies each transaction exactly once, and the trial balance stays zero.

## Extending

Implement `IdempotencyStore.get` and `put_if_absent` atomically over your database to make keys
survive restarts. Balances follow the convention that debits increase and credits decrease the
reported figure; account names are plain strings such as `cash:main` or `wallet:user-42`,
validated for length and control characters.

## Development

```console
$ pip install -e .[dev]
$ ruff check src tests examples
$ mypy
$ PYTHONPATH=src python -m unittest discover -s tests -t . -v
```

The specification in `SPEC.md` states the requirements; the tests map to them by identifier.

## License

MIT. See `LICENSE`.
