"""Concurrency tests. Maps to FR-003 and NFR-003."""

from __future__ import annotations

import threading
import unittest

from ledgerpost import (
    Direction,
    Ledger,
    MemoryIdempotencyStore,
    Money,
    Outcome,
    Posting,
    PostingEngine,
    Transaction,
)


def sale(txn_id: str, amount: int = 100) -> Transaction:
    return Transaction(
        txn_id,
        [
            Posting("cash:main", Direction.DEBIT, Money(amount, "USD")),
            Posting("income:sales", Direction.CREDIT, Money(amount, "USD")),
        ],
    )


class SameKeyRaceTests(unittest.TestCase):
    def test_concurrent_same_key_posts_exactly_once(self) -> None:
        threads = 16
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        results: list[Outcome] = []
        results_lock = threading.Lock()

        def worker(n: int) -> None:
            outcome = engine.post("evt-shared", sale(f"sale-{n}"))
            with results_lock:
                results.append(outcome)

        workers = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join()

        self.assertEqual(len(results), threads)
        replays = [outcome for outcome in results if outcome.replayed]
        fresh = [outcome for outcome in results if not outcome.replayed]
        self.assertEqual(len(fresh), 1)
        self.assertEqual(len(replays), threads - 1)
        self.assertEqual(len({outcome.transaction.id for outcome in results}), 1)
        self.assertEqual(len(ledger), 1)
        self.assertEqual(
            ledger.balance("cash:main", "USD"), Money(100, "USD")
        )


class DistinctKeyRaceTests(unittest.TestCase):
    def test_concurrent_distinct_keys_all_post(self) -> None:
        threads = 16
        ledger = Ledger()
        engine = PostingEngine(ledger, MemoryIdempotencyStore())
        start = threading.Barrier(threads)

        def worker(n: int) -> None:
            start.wait()
            engine.post(f"evt-{n}", sale(f"sale-{n}"))

        workers = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
        for thread in workers:
            thread.start()
        for thread in workers:
            thread.join()

        self.assertEqual(len(ledger), threads)
        trial = ledger.trial_balance()
        self.assertEqual(trial, {"USD": Money(0, "USD")})
        self.assertEqual(ledger.balance("cash:main", "USD"), Money(100 * threads, "USD"))


if __name__ == "__main__":
    unittest.main()
