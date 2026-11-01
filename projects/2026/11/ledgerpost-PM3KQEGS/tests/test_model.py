"""Unit tests for postings and transactions. Maps to FR-002, FR-008, FR-009."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from ledgerpost import (
    Direction,
    InsufficientPostingsError,
    InvalidPostingError,
    Money,
    Posting,
    Transaction,
    UnbalancedTransactionError,
)


def cash(amount: int, currency: str = "USD") -> Posting:
    return Posting("cash:main", Direction.DEBIT, Money(amount, currency))


def revenue(amount: int, currency: str = "USD") -> Posting:
    return Posting("income:sales", Direction.CREDIT, Money(amount, currency))


class PostingTests(unittest.TestCase):
    def test_accepts_valid_posting(self) -> None:
        posting = cash(100)
        self.assertEqual(posting.account, "cash:main")
        self.assertIs(posting.direction, Direction.DEBIT)

    def test_rejects_zero_amount(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Posting("cash:main", Direction.DEBIT, Money(0, "USD"))

    def test_rejects_negative_amount(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Posting("cash:main", Direction.DEBIT, Money(-5, "USD"))

    def test_rejects_empty_account(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Posting("", Direction.DEBIT, Money(5, "USD"))

    def test_rejects_control_characters_in_account(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Posting("cash:\nmain", Direction.DEBIT, Money(5, "USD"))

    def test_rejects_oversized_account(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Posting("a" * 121, Direction.DEBIT, Money(5, "USD"))

    def test_rejects_non_direction_value(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Posting("cash:main", "debit", Money(5, "USD"))  # type: ignore[arg-type]


class TransactionTests(unittest.TestCase):
    def test_accepts_balanced_transaction(self) -> None:
        txn = Transaction("sale-1", [cash(2500), revenue(2500)])
        self.assertEqual(len(txn.postings), 2)

    def test_accepts_list_input_converted_to_tuple(self) -> None:
        txn = Transaction("sale-1", [cash(2500), revenue(2500)])
        self.assertIsInstance(txn.postings, tuple)

    def test_rejects_single_posting(self) -> None:
        with self.assertRaises(InsufficientPostingsError):
            Transaction("sale-1", [cash(2500)])

    def test_rejects_unbalanced_transaction(self) -> None:
        with self.assertRaises(UnbalancedTransactionError):
            Transaction("sale-1", [cash(2500), revenue(2400)])

    def test_rejects_credit_only_currency(self) -> None:
        with self.assertRaises(UnbalancedTransactionError):
            Transaction(
                "sale-1",
                [cash(2500), revenue(2500), Posting("fees", Direction.CREDIT, Money(10, "EUR"))],
            )

    def test_accepts_multi_currency_balanced_transaction(self) -> None:
        txn = Transaction(
            "fx-free-1",
            [
                cash(2500),
                revenue(2500),
                Posting("cash:eur", Direction.DEBIT, Money(500, "EUR")),
                Posting("income:eur", Direction.CREDIT, Money(500, "EUR")),
            ],
        )
        self.assertEqual(len(txn.postings), 4)

    def test_rejects_empty_id(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Transaction("", [cash(1), revenue(1)])

    def test_rejects_control_characters_in_id(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Transaction("sale\n1", [cash(1), revenue(1)])

    def test_rejects_non_posting_entries(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Transaction("sale-1", [cash(1), ("income:sales", "credit", Money(1, "USD"))])  # type: ignore[list-item]

    def test_metadata_copy_is_immutable(self) -> None:
        source: dict[str, str] = {"order": "o-17"}
        txn = Transaction("sale-1", [cash(100), revenue(100)], metadata=source)
        source["order"] = "mutated"
        self.assertEqual(txn.metadata["order"], "o-17")
        with self.assertRaises(TypeError):
            txn.metadata["order"] = "other"  # type: ignore[index]

    def test_rejects_bad_metadata(self) -> None:
        with self.assertRaises(InvalidPostingError):
            Transaction("sale-1", [cash(1), revenue(1)], metadata={"": "x"})
        with self.assertRaises(InvalidPostingError):
            Transaction("sale-1", [cash(1), revenue(1)], metadata={"k": 3})  # type: ignore[dict-item]

    def test_default_metadata_empty(self) -> None:
        txn = Transaction("sale-1", [cash(1), revenue(1)])
        self.assertEqual(len(txn.metadata), 0)

    def test_is_frozen(self) -> None:
        txn = Transaction("sale-1", [cash(1), revenue(1)])
        with self.assertRaises(FrozenInstanceError):
            txn.id = "other"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
