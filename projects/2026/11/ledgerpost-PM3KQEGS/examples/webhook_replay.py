"""Simulate a payment provider that redelivers webhooks.

The same business event arrives five times, as delivery systems do by
design. The engine claims the request key once; the four redeliveries
return the recorded outcome and the ledger grows by exactly one
transaction.
"""

from __future__ import annotations

from ledgerpost import (
    Direction,
    Ledger,
    MemoryIdempotencyStore,
    Money,
    Posting,
    PostingEngine,
    Transaction,
)


def topup(txn_id: str, amount: int, currency: str = "USD") -> Transaction:
    """A wallet top-up as a balanced transaction."""
    return Transaction(
        txn_id,
        [
            Posting("cash:processor", Direction.DEBIT, Money(amount, currency)),
            Posting("wallet:user-42", Direction.CREDIT, Money(amount, currency)),
        ],
    )


def main() -> None:
    ledger = Ledger()
    engine = PostingEngine(ledger, MemoryIdempotencyStore())

    deliveries = ["attempt-1", "retry-a", "retry-b", "retry-c", "retry-d"]
    for attempt in deliveries:
        outcome = engine.post("evt_2026_1001", topup("topup-1001", 2500))
        print(f"{attempt}: replayed={outcome.replayed} txn={outcome.transaction.id}")

    print(f"transactions posted: {len(ledger)}")
    print(f"processor balance: {ledger.balance('cash:processor', 'USD').amount}")
    print(f"wallet balance: {ledger.balance('wallet:user-42', 'USD').amount}")
    print(f"trial balance: {dict(ledger.trial_balance())}")


if __name__ == "__main__":
    main()
