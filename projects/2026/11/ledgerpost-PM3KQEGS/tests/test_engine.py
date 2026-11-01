"""Unit tests for the posting engine. Maps to FR-003, FR-005, FR-006, FR-007."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from ledgerpost import (
    Direction,
    InvalidRequestKeyError,
    Ledger,
    MemoryIdempotencyStore,
    Money,
    Outcome,
    Posting,
    PostingEngine,
    Transaction,
)


def sale(txn_id: str, amount: int = 2500) -> Transaction:
    return Transaction(
        txn_id,
        [
            Posting("cash:main", Direction.DEBIT, Money(amount, "USD")),
            Posting("income:sales", Direction.CREDIT, Money(amount, "USD")),
        ],
    )


class SingleEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = Ledger()
        self.store = MemoryIdempotencyStore()
        self.engine = PostingEngine(self.ledger, self.store)

    def test_first_post_applies_and_is_fresh(self) -> None:
        outcome = self.engine.post("evt-1", sale("sale-1"))
        self.assertFalse(outcome.replayed)
        self.assertEqual(outcome.transaction.id, "sale-1")
        self.assertEqual(len(self.ledger), 1)

    def test_same_key_returns_recorded_transaction_as_replay(self) -> None:
        first = self.engine.post("evt-1", sale("sale-1"))
        second = self.engine.post("evt-1", sale("sale-1-variant"))
        self.assertTrue(second.replayed)
        self.assertEqual(second.transaction.id, first.transaction.id)
        self.assertNotEqual(second.transaction.id, "sale-1-variant")
        self.assertEqual(len(self.ledger), 1)

    def test_replay_outcome_matches_first_except_flag(self) -> None:
        first = self.engine.post("evt-1", sale("sale-1"))
        second = self.engine.post("evt-1", sale("ignored"))
        self.assertEqual(second.transaction, first.transaction)
        self.assertTrue(second.replayed)
        self.assertFalse(first.replayed)

    def test_different_keys_post_equal_transactions_twice(self) -> None:
        self.engine.post("evt-1", sale("sale-1"))
        self.engine.post("evt-2", sale("sale-1"))
        self.assertEqual(len(self.ledger), 2)

    def test_rejected_request_key(self) -> None:
        for bad in ("", " " + "\x00", "k" * 257, "bad\nkey"):
            with self.subTest(bad=bad):
                with self.assertRaises(InvalidRequestKeyError):
                    self.engine.post(bad, sale("sale-1"))

    def test_outcome_is_immutable(self) -> None:
        outcome = self.engine.post("evt-1", sale("sale-1"))
        with self.assertRaises(FrozenInstanceError):
            outcome.replayed = True  # type: ignore[misc]


class StoreProtocolTests(unittest.TestCase):
    def test_memory_store_satisfies_protocol(self) -> None:
        store = MemoryIdempotencyStore()
        outcome = Outcome(transaction=sale("sale-1"), replayed=False)
        claimed, winner = store.put_if_absent("k", outcome)
        self.assertTrue(claimed)
        self.assertIs(winner, outcome)
        again, _ = store.put_if_absent("k", Outcome(transaction=sale("sale-2"), replayed=False))
        self.assertFalse(again)
        self.assertIs(store.get("k"), outcome)
        self.assertIsNone(store.get("missing"))

    def test_engine_works_against_alternate_store(self) -> None:
        class RecordingStore:
            def __init__(self) -> None:
                self.values: dict[str, Outcome] = {}

            def get(self, key: str) -> Outcome | None:
                return self.values.get(key)

            def put_if_absent(self, key: str, value: Outcome) -> tuple[bool, Outcome]:
                existing = self.values.get(key)
                if existing is not None:
                    return False, existing
                self.values[key] = value
                return True, value

        ledger = Ledger()
        engine = PostingEngine(ledger, RecordingStore())
        outcome = engine.post("evt-9", sale("sale-9"))
        self.assertFalse(outcome.replayed)
        self.assertEqual(len(ledger), 1)


class DeterminismTests(unittest.TestCase):
    def test_no_hidden_state_between_runs(self) -> None:
        def run() -> tuple[Outcome, int]:
            ledger = Ledger()
            engine = PostingEngine(ledger, MemoryIdempotencyStore())
            return engine.post("evt-1", sale("sale-1")), len(ledger)

        first, first_len = run()
        second, second_len = run()
        self.assertEqual(first.transaction, second.transaction)
        self.assertEqual(first.replayed, second.replayed)
        self.assertEqual(first_len, second_len)


if __name__ == "__main__":
    unittest.main()
