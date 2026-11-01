"""Append-only ledger with running balances."""

from __future__ import annotations

import threading

from .model import Direction, Transaction
from .money import Money


class Ledger:
    """Holds posted transactions and answers balance queries.

    Balances follow the accounting convention that debits increase and
    credits decrease the returned figure: an asset account fed by
    debits grows positive, a liability account fed by credits goes
    negative.  Every mutation takes a lock, so one ledger instance can
    serve concurrent posting threads.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._transactions: list[Transaction] = []
        # (account, currency) -> net minor units, debits minus credits.
        self._nets: dict[tuple[str, str], int] = {}

    def apply(self, transaction: Transaction) -> None:
        """Append ``transaction`` and update running balances."""
        with self._lock:
            self._transactions.append(transaction)
            for posting in transaction.postings:
                key = (posting.account, posting.amount.currency)
                signed = posting.amount.amount
                if posting.direction is Direction.CREDIT:
                    signed = -signed
                self._nets[key] = self._nets.get(key, 0) + signed

    def balance(self, account: str, currency: str | None = None) -> Money | dict[str, Money]:
        """Return the balance of ``account``.

        With ``currency`` the result is a single :class:`Money` value
        (zero when the account never traded that currency).  Without it
        the result is a mapping from every currency the account touched
        to its balance in that currency.
        """
        with self._lock:
            if currency is not None:
                return Money(self._nets.get((account, currency), 0), currency)
            per_currency: dict[str, Money] = {}
            for (acct, curr), net in self._nets.items():
                if acct == account:
                    per_currency[curr] = Money(net, curr)
            return per_currency

    def trial_balance(self) -> dict[str, Money]:
        """Sum the net balance of every account, per currency.

        For a ledger fed only balanced transactions every figure is
        zero; a non-zero figure means postings bypassed the balance
        check somewhere upstream.
        """
        with self._lock:
            totals: dict[str, int] = {}
            for (_acct, curr), net in self._nets.items():
                totals[curr] = totals.get(curr, 0) + net
            return {curr: Money(net, curr) for curr, net in sorted(totals.items())}

    def transactions(self) -> tuple[Transaction, ...]:
        """Return a snapshot of the posted transactions, in apply order."""
        with self._lock:
            return tuple(self._transactions)

    def __len__(self) -> int:
        with self._lock:
            return len(self._transactions)
