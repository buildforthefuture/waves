"""Typed errors raised by ledgerpost.

Every error derives from :class:`LedgerpostError`, so callers can catch
the whole family with one handler while still matching specific cases.
"""

from __future__ import annotations


class LedgerpostError(Exception):
    """Base class for every error raised by this package."""


class MoneyError(LedgerpostError):
    """Invalid money value or an operation on mismatched currencies."""


class InvalidAmountError(MoneyError):
    """The amount is not an integer number of minor units."""


class CurrencyCodeError(MoneyError):
    """The currency code is not three uppercase ASCII letters."""


class CurrencyMismatchError(MoneyError):
    """An operation mixed two different currencies."""


class TransactionError(LedgerpostError):
    """Invalid transaction structure."""


class InsufficientPostingsError(TransactionError):
    """A transaction was built from fewer than two postings."""


class UnbalancedTransactionError(TransactionError):
    """Debit and credit totals differ for at least one currency."""


class InvalidPostingError(TransactionError):
    """A posting has an unusable account name or a non-positive amount."""


class StoreError(LedgerpostError):
    """The idempotency store was used incorrectly."""


class InvalidRequestKeyError(StoreError):
    """The request key is empty, too long, or contains control characters."""
