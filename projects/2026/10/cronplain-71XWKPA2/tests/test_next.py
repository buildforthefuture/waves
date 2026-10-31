"""Next and previous run computation (FR-6, FR-7, NFR-3)."""

from __future__ import annotations

import unittest
from datetime import datetime

from cronplain.fields import NoMatchError
from cronplain.schedule import parse


class NextRunTest(unittest.TestCase):
    """FR-6: next-run computation skips impossible dates and terminates."""

    def test_strictly_after(self) -> None:
        """FR-6: the result is always strictly after the reference moment."""
        schedule = parse("0 * * * *")
        self.assertEqual(
            schedule.next_after(datetime(2026, 11, 1, 14, 0)), datetime(2026, 11, 1, 15, 0)
        )
        self.assertEqual(
            schedule.next_after(datetime(2026, 11, 1, 14, 30, 30)), datetime(2026, 11, 1, 15, 0)
        )

    def test_short_months_are_skipped(self) -> None:
        """FR-6: day 31 skips months that have no day 31."""
        schedule = parse("0 0 31 * *")
        self.assertEqual(schedule.next_after(datetime(2026, 2, 1)), datetime(2026, 3, 31))
        self.assertEqual(schedule.next_after(datetime(2026, 1, 30)), datetime(2026, 1, 31))

    def test_leap_years(self) -> None:
        """FR-6: February 29 only matches in leap years."""
        schedule = parse("0 0 29 2 *")
        self.assertEqual(schedule.next_after(datetime(2026, 11, 1)), datetime(2028, 2, 29))

    def test_never_matching_schedule(self) -> None:
        """FR-6: 0 0 31 2 * can never match and reports that clearly."""
        schedule = parse("0 0 31 2 *")
        with self.assertRaises(NoMatchError):
            schedule.next_after(datetime(2026, 1, 1))

    def test_weekend_rollover(self) -> None:
        """FR-6: a weekday schedule jumps the weekend to Monday."""
        schedule = parse("0 9 * * 1-5")
        self.assertEqual(
            schedule.next_after(datetime(2026, 11, 6, 17, 30)), datetime(2026, 11, 9, 9, 0)
        )

    def test_month_jump(self) -> None:
        """FR-6: restricted months are jumped as a unit."""
        schedule = parse("0 0 1 3 *")
        self.assertEqual(schedule.next_after(datetime(2026, 11, 1)), datetime(2027, 3, 1))

    def test_next_n(self) -> None:
        """FR-6: several following runs are returned in order."""
        schedule = parse("*/15 * * * *")
        runs = schedule.next_n(datetime(2026, 11, 1, 9, 50), 3)
        self.assertEqual(
            runs,
            [
                datetime(2026, 11, 1, 10, 0),
                datetime(2026, 11, 1, 10, 15),
                datetime(2026, 11, 1, 10, 30),
            ],
        )


class PreviousRunTest(unittest.TestCase):
    """FR-7: previous-run computation mirrors next-run semantics."""

    def test_hourly(self) -> None:
        """FR-7: previous hourly run respects strictness and seconds."""
        schedule = parse("@hourly")
        self.assertEqual(
            schedule.previous_before(datetime(2026, 11, 1, 14, 30, 30)),
            datetime(2026, 11, 1, 14, 0),
        )
        self.assertEqual(
            schedule.previous_before(datetime(2026, 11, 1, 14, 0, 0)), datetime(2026, 11, 1, 13, 0)
        )

    def test_monthly(self) -> None:
        """FR-7: previous monthly run crosses month boundaries."""
        schedule = parse("0 0 1 * *")
        self.assertEqual(schedule.previous_before(datetime(2026, 3, 15)), datetime(2026, 3, 1))
        self.assertEqual(schedule.previous_before(datetime(2026, 3, 1)), datetime(2026, 2, 1))

    def test_previous_leap(self) -> None:
        """FR-7: previous February 29 lands on the earlier leap year."""
        schedule = parse("0 0 29 2 *")
        self.assertEqual(schedule.previous_before(datetime(2028, 1, 1)), datetime(2024, 2, 29))

    def test_previous_restricted_month(self) -> None:
        """FR-7: months outside the schedule are skipped backwards."""
        schedule = parse("0 0 1 3 *")
        self.assertEqual(schedule.previous_before(datetime(2026, 11, 15)), datetime(2026, 3, 1))


class PerformanceTest(unittest.TestCase):
    """NFR-3: answers stay fast across long spans and repeated parsing."""

    def test_parse_throughput(self) -> None:
        """NFR-3: one thousand parses complete in under a second."""
        import time

        start = time.monotonic()
        for _ in range(1000):
            parse("*/10 9-17 * * 1-5")
        self.assertLess(time.monotonic() - start, 1.0)

    def test_far_next_run(self) -> None:
        """NFR-3: an eight-year leap-year span resolves in under a second."""
        import time

        schedule = parse("0 0 29 2 *")
        start = time.monotonic()
        result = schedule.next_after(datetime(2096, 3, 1))
        elapsed = time.monotonic() - start
        self.assertEqual(result, datetime(2104, 2, 29))
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()


class PreviousNeverMatchTest(unittest.TestCase):
    """FR-7: a schedule matching no date reports it instead of looping."""

    def test_previous_never_matching(self) -> None:
        """FR-7: 0 0 31 2 * has no previous run and reports that clearly."""
        schedule = parse("0 0 31 2 *")
        with self.assertRaises(NoMatchError):
            schedule.previous_before(datetime(2026, 6, 1))
