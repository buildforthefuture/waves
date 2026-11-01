"""Performance check for NFR-004: ten thousand sequential postings inside five seconds."""

from __future__ import annotations

import time
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


class PerformanceTests(unittest.TestCase):
    def test_ten_thousand_postings_within_five_seconds(self) -> None:
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        start = time.perf_counter()
        for n in range(10_000):
            engine.post(
                f"evt_{n}",
                Transaction(
                    f"txn_{n}",
                    [
                        Posting("cash:main", Direction.DEBIT, Money(100, "USD")),
                        Posting("income:main", Direction.CREDIT, Money(100, "USD")),
                    ],
                ),
            )
        elapsed = time.perf_counter() - start
        self.assertEqual(len(ledger), 10_000)
        self.assertLess(elapsed, 5.0, f"ten thousand postings took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
