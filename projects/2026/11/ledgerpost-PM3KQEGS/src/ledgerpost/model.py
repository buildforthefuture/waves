"""Core value objects: postings, transactions, outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

from .errors import InsufficientPostingsError, InvalidPostingError, UnbalancedTransactionError
from .money import Money

MAX_ACCOUNT_LEN = 120
MAX_ID_LEN = 128
MAX_META_KEY_LEN = 64
MAX_META_VALUE_LEN = 256


class Direction(str, Enum):
    """Which side of an account a posting touches."""

    DEBIT = "debit"
    CREDIT = "credit"


def _validate_account(account: str) -> None:
    if not isinstance(account, str) or not account:
        raise InvalidPostingError("account must be a non-empty string")
    if len(account) > MAX_ACCOUNT_LEN:
        raise InvalidPostingError(f"account longer than {MAX_ACCOUNT_LEN} characters")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in account):
        raise InvalidPostingError("account must not contain control characters")


@dataclass(frozen=True, slots=True)
class Posting:
    """One leg of a transaction: an account, a side, and a positive amount."""

    account: str
    direction: Direction
    amount: Money

    def __post_init__(self) -> None:
        _validate_account(self.account)
        if not isinstance(self.direction, Direction):
            raise InvalidPostingError("direction must be a Direction value")
        if self.amount.amount <= 0:
            raise InvalidPostingError("posting amounts must be positive; use direction for sign")


def _balance(postings: tuple[Posting, ...]) -> None:
    debits: dict[str, int] = {}
    credits: dict[str, int] = {}
    for posting in postings:
        book = debits if posting.direction is Direction.DEBIT else credits
        book[posting.amount.currency] = (
            book.get(posting.amount.currency, 0) + posting.amount.amount
        )
    for currency, debit_total in debits.items():
        if debit_total != credits.get(currency, 0):
            raise UnbalancedTransactionError(
                f"debit and credit totals differ for {currency}: "
                f"{debit_total} != {credits.get(currency, 0)}"
            )
    for currency in credits:
        if currency not in debits:
            raise UnbalancedTransactionError(
                f"currency {currency} has credits with no debits"
            )


@dataclass(frozen=True, slots=True)
class Transaction:
    """A balanced set of postings under a caller-assigned identifier.

    Balancing is enforced per currency: a transaction may move several
    currencies at once as long as each currency's debits equal its
    credits.  The identifier comes from the caller so that posting the
    same business event twice under one idempotency key yields byte
    identical outcomes.
    """

    id: str
    postings: tuple[Posting, ...]
    metadata: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id:
            raise InvalidPostingError("transaction id must be a non-empty string")
        if len(self.id) > MAX_ID_LEN:
            raise InvalidPostingError(f"transaction id longer than {MAX_ID_LEN} characters")
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in self.id):
            raise InvalidPostingError("transaction id must not contain control characters")
        if isinstance(self.postings, list):
            object.__setattr__(self, "postings", tuple(self.postings))
        if len(self.postings) < 2:
            raise InsufficientPostingsError(
                f"a transaction needs at least two postings, got {len(self.postings)}"
            )
        for posting in self.postings:
            if not isinstance(posting, Posting):
                raise InvalidPostingError(f"expected Posting, got {type(posting).__name__}")
        _balance(self.postings)
        if self.metadata is None:
            object.__setattr__(self, "metadata", MappingProxyType({}))
        else:
            cleaned: dict[str, str] = {}
            for key, value in dict(self.metadata).items():
                if not isinstance(key, str) or not key or len(key) > MAX_META_KEY_LEN:
                    raise InvalidPostingError(f"metadata key unusable: {key!r}")
                if not isinstance(value, str) or len(value) > MAX_META_VALUE_LEN:
                    raise InvalidPostingError(f"metadata value unusable for key {key!r}")
                cleaned[key] = value
            object.__setattr__(self, "metadata", MappingProxyType(cleaned))


@dataclass(frozen=True, slots=True)
class Outcome:
    """The result of one posting request.

    ``replayed`` is false on the call that first claimed the request key
    and true on every later call that returns the recorded transaction.
    """

    transaction: Transaction
    replayed: bool
