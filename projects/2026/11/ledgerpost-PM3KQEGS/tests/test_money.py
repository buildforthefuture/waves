"""Unit tests for the Money value object. Maps to FR-001, NFR-002."""

from __future__ import annotations

import unittest

from ledgerpost import (
    CurrencyCodeError,
    CurrencyMismatchError,
    InvalidAmountError,
    Money,
)


class ConstructionTests(unittest.TestCase):
    def test_accepts_integer_minor_units(self) -> None:
        money = Money(1050, "USD")
        self.assertEqual(money.amount, 1050)
        self.assertEqual(money.currency, "USD")

    def test_rejects_float_amounts(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Money(10.50, "USD")  # type: ignore[arg-type]

    def test_rejects_bool_amounts(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Money(True, "USD")  # type: ignore[arg-type]

    def test_rejects_non_integer_amounts(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Money("1050", "USD")  # type: ignore[arg-type]

    def test_rejects_bad_currency_codes(self) -> None:
        for bad in ("usd", "US", "USDD", "US1", "", "  USD"):
            with self.subTest(bad=bad):
                with self.assertRaises(CurrencyCodeError):
                    Money(1, bad)

    def test_zero_helper(self) -> None:
        self.assertEqual(Money.zero("JPY").amount, 0)


class ArithmeticTests(unittest.TestCase):
    def test_add_and_subtract(self) -> None:
        a = Money(1000, "EUR")
        b = Money(220, "EUR")
        self.assertEqual((a + b).amount, 1220)
        self.assertEqual((a - b).amount, 780)

    def test_addition_is_exact_in_minor_units(self) -> None:
        # 0.10 + 0.20 in floats is 0.30000000000000004; in minor units it is 30.
        self.assertEqual((Money(10, "USD") + Money(20, "USD")).amount, 30)

    def test_mismatched_currency_rejected(self) -> None:
        with self.assertRaises(CurrencyMismatchError):
            Money(100, "USD") + Money(100, "EUR")

    def test_negate_and_abs(self) -> None:
        self.assertEqual((-Money(50, "GBP")).amount, -50)
        self.assertEqual(abs(Money(-50, "GBP")).amount, 50)

    def test_scaled_requires_int(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Money(100, "USD").scaled(1.5)  # type: ignore[arg-type]

    def test_scaled_multiplies_exactly(self) -> None:
        self.assertEqual(Money(333, "USD").scaled(3).amount, 999)


class ComparisonTests(unittest.TestCase):
    def test_ordering(self) -> None:
        self.assertLess(Money(1, "USD"), Money(2, "USD"))
        self.assertGreater(Money(2, "USD"), Money(1, "USD"))
        self.assertLessEqual(Money(2, "USD"), Money(2, "USD"))

    def test_ordering_mismatch_rejected(self) -> None:
        with self.assertRaises(CurrencyMismatchError):
            _ = Money(1, "USD") < Money(1, "EUR")

    def test_equality_requires_currency(self) -> None:
        self.assertNotEqual(Money(1, "USD"), Money(1, "EUR"))

    def test_hashable(self) -> None:
        self.assertEqual(len({Money(1, "USD"), Money(1, "USD"), Money(2, "USD")}), 2)

    def test_is_zero(self) -> None:
        self.assertTrue(Money(0, "CHF").is_zero())
        self.assertFalse(Money(1, "CHF").is_zero())


class AllocationTests(unittest.TestCase):
    def test_allocate_sums_back_exactly(self) -> None:
        parts = Money(1050, "USD").allocate([1, 1, 1])
        self.assertEqual(sum(part.amount for part in parts), 1050)
        self.assertEqual([part.amount for part in parts], [350, 350, 350])

    def test_largest_remainder_goes_to_first_largest_ratio(self) -> None:
        parts = Money(5, "USD").allocate([1, 1, 1])
        self.assertEqual([part.amount for part in parts], [2, 2, 1])

    def test_uneven_ratios(self) -> None:
        parts = Money(1000, "EUR").allocate([5, 3, 2])
        self.assertEqual([part.amount for part in parts], [500, 300, 200])

    def test_split_into_parts(self) -> None:
        parts = Money(1001, "USD").split(4)
        self.assertEqual([part.amount for part in parts], [251, 250, 250, 250])
        self.assertEqual(sum(part.amount for part in parts), 1001)

    def test_rejects_bad_ratios(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Money(10, "USD").allocate([])
        with self.assertRaises(InvalidAmountError):
            Money(10, "USD").allocate([0])
        with self.assertRaises(InvalidAmountError):
            Money(10, "USD").allocate([-1])

    def test_rejects_bad_parts(self) -> None:
        with self.assertRaises(InvalidAmountError):
            Money(10, "USD").split(0)


if __name__ == "__main__":
    unittest.main()
