"""Ledgerpost: an embeddable idempotent double-entry posting engine.

Payment-adjacent services receive the same business event more than
once: webhooks retry, clients resend after timeouts, jobs re-run after
crashes.  Ledgerpost pairs an idempotency store with a double-entry
ledger so each repeated delivery returns the original outcome instead
of posting again, and every transaction it accepts balances per
currency by construction.
"""

from __future__ import annotations

from .engine import PostingEngine
from .errors import (
    CurrencyCodeError,
    CurrencyMismatchError,
    InsufficientPostingsError,
    InvalidAmountError,
    InvalidPostingError,
    InvalidRequestKeyError,
    LedgerpostError,
    MoneyError,
    StoreError,
    TransactionError,
    UnbalancedTransactionError,
)
from .ledger import Ledger
from .model import Direction, Outcome, Posting, Transaction
from .money import Money
from .store import IdempotencyStore, MemoryIdempotencyStore

__version__ = "0.1.0"

__all__ = [
    "CurrencyCodeError",
    "CurrencyMismatchError",
    "Direction",
    "IdempotencyStore",
    "InsufficientPostingsError",
    "InvalidAmountError",
    "InvalidPostingError",
    "InvalidRequestKeyError",
    "Ledger",
    "LedgerpostError",
    "MemoryIdempotencyStore",
    "Money",
    "MoneyError",
    "Outcome",
    "Posting",
    "PostingEngine",
    "StoreError",
    "Transaction",
    "TransactionError",
    "UnbalancedTransactionError",
    "__version__",
]
