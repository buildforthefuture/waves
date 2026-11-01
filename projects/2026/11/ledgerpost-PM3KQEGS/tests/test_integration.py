"""Integration tests: at-least-once delivery flows. Maps to FR-003, FR-004, NFR-001."""

from __future__ import annotations

import random
import unittest

from ledgerpost import (
    Direction,
    Ledger,
    MemoryIdempotencyStore,
    Money,
    Posting,
    PostingEngine,
    Transaction,
)


def delivery_event(key: str, txn_id: str, amount: int) -> Transaction:
    """A wallet top-up expressed as a balanced transaction."""
    return Transaction(
        txn_id,
        [
            Posting("cash:processor", Direction.DEBIT, Money(amount, "USD")),
            Posting("wallet:user-42", Direction.CREDIT, Money(amount, "USD")),
        ],
    )


class AtLeastOnceDeliveryTests(unittest.TestCase):
    def test_retried_deliveries_post_once(self) -> None:
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        for _ in range(5):
            engine.post("evt_100", delivery_event("evt_100", "topup-100", 3000))
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger.balance("wallet:user-42", "USD"), Money(-3000, "USD"))

    def test_out_of_order_retries_across_events(self) -> None:
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        deliveries = [
            ("evt_3", "topup-3", 300),
            ("evt_1", "topup-1", 100),
            ("evt_2", "topup-2", 200),
        ]
        for key, txn_id, amount in deliveries:
            engine.post(key, delivery_event(key, txn_id, amount))
        # A duplicate of the first event arrives last.
        engine.post("evt_1", delivery_event("evt_1", "topup-1", 100))
        self.assertEqual(len(ledger), 3)
        self.assertEqual(ledger.balance("wallet:user-42", "USD"), Money(-600, "USD"))
        self.assertEqual(
            ledger.trial_balance(), {"USD": Money(0, "USD")}
        )

    def test_distinct_events_never_share_outcomes(self) -> None:
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        for n in range(10):
            outcome = engine.post(f"evt_{n}", delivery_event(f"evt_{n}", f"topup-{n}", 100 + n))
            self.assertFalse(outcome.replayed)
        self.assertEqual(len(ledger), 10)


class RandomizedBalanceTests(unittest.TestCase):
    def test_two_hundred_random_transactions_stay_balanced(self) -> None:
        rng = random.Random(20261101)
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        for n in range(200):
            amount = rng.randrange(1, 100_000)
            currency = rng.choice(["USD", "EUR", "JPY"])
            key = f"evt_{n}"
            engine.post(
                key,
                Transaction(
                    f"txn_{n}",
                    [
                        Posting("cash:main", Direction.DEBIT, Money(amount, currency)),
                        Posting("income:main", Direction.CREDIT, Money(amount, currency)),
                    ],
                ),
            )
        expected = {currency: Money(0, currency) for currency in ("USD", "EUR", "JPY")}
        self.assertEqual(ledger.trial_balance(), expected)
        self.assertEqual(len(ledger), 200)


if __name__ == "__main__":
    unittest.main()


class SourceHygieneTests(unittest.TestCase):
    def test_no_clock_or_random_identifier_imports_in_package(self) -> None:
        import re
        from pathlib import Path

        banned = re.compile(r"^\s*(?:import|from)\s+(time|uuid|datetime)\b", re.MULTILINE)
        root = Path(__file__).resolve().parents[1] / "src" / "ledgerpost"
        for source in sorted(root.glob("*.py")):
            with self.subTest(module=source.name):
                self.assertIsNone(banned.search(source.read_text(encoding="utf-8")))
