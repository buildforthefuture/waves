"""Deterministic plain-English descriptions (FR-8)."""

from __future__ import annotations

import unittest

from cronplain import describe


class DescribeTest(unittest.TestCase):
    """FR-8: accepted expressions render with stable, readable wording."""

    CASES = [
        ("* * * * *", "Every minute."),
        ("*/15 * * * *", "Every 15 minutes."),
        ("0 9 * * 1-5", "At 09:00, on Monday through Friday."),
        ("0 0 1 * 1", "At 00:00, on day 1 of the month or on Monday."),
        ("0 */6 * * *", "At 00:00, 06:00, 12:00 and 18:00."),
        ("@daily", "At 00:00."),
        ("0 0 1 1 *", "At 00:00, on day 1 of the month, in January."),
        (
            "*/10 9-17 * * 1-5",
            "Every 10 minutes past every hour from 9 through 17, "
            "on Monday through Friday.",
        ),
        (
            "0 0 */5 * 1",
            "At 00:00, on every 5th day of the month that is also Monday.",
        ),
        (
            "0 0 1-7 JAN-MAR *",
            "At 00:00, on day 1 through 7 of the month, in January through March.",
        ),
        ("0 0 * * 7", "At 00:00, on Sunday."),
        ("30 8,12 * * *", "At 08:30 and 12:30."),
        ("0 12 * JAN *", "At 12:00, in January."),
        ("0 0 1-31 * 1", "At 00:00."),
    ]

    def test_golden_strings(self) -> None:
        """FR-8: each expression renders to its pinned description."""
        for expression, expected in self.CASES:
            with self.subTest(expression=expression):
                self.assertEqual(describe(expression), expected)

    def test_deterministic(self) -> None:
        """FR-8: repeated calls return identical text."""
        for expression, _ in self.CASES:
            self.assertEqual(describe(expression), describe(expression))

    def test_equivalent_forms_describe_alike(self) -> None:
        """FR-8: equivalent expressions share one description."""
        self.assertEqual(describe("0 0 * * 0"), describe("0 0 * * 7"))
        self.assertEqual(describe("0 0 * * SUN"), describe("0 0 * * 0"))


if __name__ == "__main__":
    unittest.main()
