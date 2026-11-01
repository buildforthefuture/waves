"""Monetary amounts as integer minor units.

A :class:`Money` value is an ``int`` count of minor units (cents for most
currencies) plus a three-letter currency code.  Floating-point input is
rejected outright: monetary values that pass through binary floats pick
up rounding noise that a ledger cannot absorb.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .errors import CurrencyCodeError, CurrencyMismatchError, InvalidAmountError

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class Money:
    """An immutable amount of one currency in minor units."""

    amount: int
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount, bool) or not isinstance(self.amount, int):
            raise InvalidAmountError(
                f"amount must be an int of minor units, got {type(self.amount).__name__}"
            )
        if not isinstance(self.currency, str) or not _CURRENCY_RE.fullmatch(self.currency):
            raise CurrencyCodeError(
                f"currency must be three uppercase letters, got {self.currency!r}"
            )

    # -- construction helpers ------------------------------------------------

    @classmethod
    def zero(cls, currency: str) -> Money:
        """Return a zero amount of ``currency``."""
        return cls(0, currency)

    # -- arithmetic ----------------------------------------------------------

    def _require_same_currency(self, other: Money, op: str) -> None:
        if not isinstance(other, Money):
            raise InvalidAmountError(f"cannot {op} Money with {type(other).__name__}")
        if other.currency != self.currency:
            raise CurrencyMismatchError(
                f"cannot {op} {self.currency} with {other.currency}"
            )

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other, "add")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other, "subtract")
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    def scaled(self, factor: int) -> Money:
        """Return the amount multiplied by an integer factor.

        Splitting or repeating an exact amount never needs fractions, so
        only integer factors are accepted.
        """
        if isinstance(factor, bool) or not isinstance(factor, int):
            raise InvalidAmountError(f"factor must be an int, got {type(factor).__name__}")
        return Money(self.amount * factor, self.currency)

    # -- comparisons ---------------------------------------------------------

    def _require_comparable(self, other: Money) -> None:
        if not isinstance(other, Money):
            return
        if other.currency != self.currency:
            raise CurrencyMismatchError(
                f"cannot order {self.currency} against {other.currency}"
            )

    def __lt__(self, other: Money) -> bool:
        self._require_comparable(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._require_comparable(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._require_comparable(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._require_comparable(other)
        return self.amount >= other.amount

    def is_zero(self) -> bool:
        """Return whether the amount is zero."""
        return self.amount == 0

    # -- allocation ----------------------------------------------------------

    def allocate(self, ratios: Sequence[int]) -> tuple[Money, ...]:
        """Split the amount across positive integer ratios, losslessly.

        Uses the largest-remainder method: the parts sum back to exactly
        this amount, and any rounding remainder lands on the earliest
        largest share.
        """
        if not ratios:
            raise InvalidAmountError("allocate needs at least one ratio")
        cleaned: list[int] = []
        for ratio in ratios:
            if isinstance(ratio, bool) or not isinstance(ratio, int) or ratio <= 0:
                raise InvalidAmountError(f"ratios must be positive ints, got {ratio!r}")
            cleaned.append(ratio)
        total = sum(cleaned)
        shares = [self.amount * ratio // total for ratio in cleaned]
        remainder = self.amount - sum(shares)
        order = sorted(range(len(cleaned)), key=lambda i: (cleaned[i], -i), reverse=True)
        for index in order[:remainder]:
            shares[index] += 1
        return tuple(Money(part, self.currency) for part in shares)

    def split(self, parts: int) -> tuple[Money, ...]:
        """Divide the amount into ``parts`` near-equal shares, losslessly."""
        if isinstance(parts, bool) or not isinstance(parts, int) or parts <= 0:
            raise InvalidAmountError(f"parts must be a positive int, got {parts!r}")
        return self.allocate([1] * parts)
