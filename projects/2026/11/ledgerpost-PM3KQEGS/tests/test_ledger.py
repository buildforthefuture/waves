"""Unit tests for balances and the trial balance. Maps to FR-004."""

from __future__ import annotations

import unittest

from ledgerpost import (
    Direction,
    Ledger,
    Money,
    Posting,
    Transaction,
)


def txn(txn_id: str, debit_account: str, credit_account: str, amount: int, currency: str = "USD"):
    return Transaction(
        txn_id,
        [
            Posting(debit_account, Direction.DEBIT, Money(amount, currency)),
            Posting(credit_account, Direction.CREDIT, Money(amount, currency)),
        ],
    )


class BalanceTests(unittest.TestCase):
    def test_debits_increase_balance(self) -> None:
        ledger = Ledger()
        ledger.apply(txn("t1", "cash:main", "income:sales", 2500))
        self.assertEqual(ledger.balance("cash:main", "USD"), Money(2500, "USD"))

    def test_credits_decrease_balance(self) -> None:
        ledger = Ledger()
        ledger.apply(txn("t1", "cash:main", "income:sales", 2500))
        self.assertEqual(ledger.balance("income:sales", "USD"), Money(-2500, "USD"))

    def test_balance_accumulates_over_transactions(self) -> None:
        ledger = Ledger()
        ledger.apply(txn("t1", "cash:main", "income:sales", 2500))
        ledger.apply(txn("t2", "cash:main", "income:sales", 1750))
        self.assertEqual(ledger.balance("cash:main", "USD"), Money(4250, "USD"))

    def test_unknown_account_is_zero(self) -> None:
        ledger = Ledger()
        self.assertEqual(ledger.balance("ghost", "USD"), Money(0, "USD"))

    def test_full_balance_mapping(self) -> None:
        ledger = Ledger()
        ledger.apply(txn("t1", "cash:main", "income:sales", 2500))
        ledger.apply(
            Transaction(
                "t2",
                [
                    Posting("cash:main", Direction.DEBIT, Money(500, "EUR")),
                    Posting("income:sales", Direction.CREDIT, Money(500, "EUR")),
                ],
            )
        )
        balances = ledger.balance("cash:main")
        self.assertEqual(balances, {"USD": Money(2500, "USD"), "EUR": Money(500, "EUR")})

    def test_trial_balance_is_zero_per_currency(self) -> None:
        ledger = Ledger()
        ledger.apply(txn("t1", "cash:main", "income:sales", 2500))
        ledger.apply(
            Transaction(
                "t2",
                [
                    Posting("cash:eur", Direction.DEBIT, Money(900, "EUR")),
                    Posting("income:eur", Direction.CREDIT, Money(900, "EUR")),
                ],
            )
        )
        self.assertEqual(
            ledger.trial_balance(), {"USD": Money(0, "USD"), "EUR": Money(0, "EUR")}
        )

    def test_empty_ledger_trial_balance(self) -> None:
        self.assertEqual(Ledger().trial_balance(), {})

    def test_transactions_snapshot_in_order(self) -> None:
        ledger = Ledger()
        ledger.apply(txn("t1", "a", "b", 100))
        ledger.apply(txn("t2", "a", "b", 200))
        self.assertEqual([t.id for t in ledger.transactions()], ["t1", "t2"])
        snapshot = ledger.transactions()
        self.assertIsInstance(snapshot, tuple)

    def test_len_counts_transactions(self) -> None:
        ledger = Ledger()
        self.assertEqual(len(ledger), 0)
        ledger.apply(txn("t1", "a", "b", 100))
        self.assertEqual(len(ledger), 1)


if __name__ == "__main__":
    unittest.main()
