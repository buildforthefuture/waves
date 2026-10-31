"""Schedule matching, including the day-field combination rule (FR-1, FR-5)."""

from __future__ import annotations

import unittest
from datetime import datetime

from cronplain.schedule import parse


class MatchingTest(unittest.TestCase):
    """FR-1: parsed schedules match the expected wall-clock minutes."""

    def test_full_grammar_schedule(self) -> None:
        """FR-1: combined constructs match only the expected minutes."""
        schedule = parse("*/15 0,12 1-7 JAN *")
        self.assertTrue(schedule.matches(datetime(2026, 1, 5, 0, 15)))
        self.assertTrue(schedule.matches(datetime(2026, 1, 7, 12, 45)))
        self.assertFalse(schedule.matches(datetime(2026, 1, 8, 0, 15)))
        self.assertFalse(schedule.matches(datetime(2026, 4, 1, 0, 15)))
        self.assertFalse(schedule.matches(datetime(2026, 1, 5, 1, 15)))

    def test_minute_and_hour_gates(self) -> None:
        """FR-1: minutes, hours, and months gate independently."""
        schedule = parse("30 2 1 3 *")
        self.assertTrue(schedule.matches(datetime(2027, 3, 1, 2, 30)))
        self.assertFalse(schedule.matches(datetime(2027, 3, 1, 2, 29)))
        self.assertFalse(schedule.matches(datetime(2027, 4, 1, 2, 30)))


class DayCombinationRuleTest(unittest.TestCase):
    """FR-5: the standard day-of-month/day-of-week combination rule."""

    def test_either_or_when_both_restricted(self) -> None:
        """FR-5: 0 0 1 * 1 fires on the 1st of the month or on any Monday."""
        schedule = parse("0 0 1 * 1")
        self.assertTrue(schedule.matches(datetime(2026, 11, 1, 0, 0)))   # day 1, Sunday
        self.assertTrue(schedule.matches(datetime(2026, 11, 2, 0, 0)))   # Monday
        self.assertFalse(schedule.matches(datetime(2026, 11, 3, 0, 0)))  # neither

    def test_dow_only(self) -> None:
        """FR-5: with day-of-month unrestricted, only weekdays apply."""
        schedule = parse("0 0 * * 1-5")
        self.assertTrue(schedule.matches(datetime(2026, 11, 2, 0, 0)))   # Monday
        self.assertFalse(schedule.matches(datetime(2026, 11, 7, 0, 0)))  # Saturday

    def test_dom_only(self) -> None:
        """FR-5: with day-of-week unrestricted, only month days apply."""
        schedule = parse("0 0 */5 * *")
        self.assertTrue(schedule.matches(datetime(2026, 11, 1, 0, 0)))   # day 1
        self.assertTrue(schedule.matches(datetime(2026, 11, 6, 0, 0)))   # day 6
        self.assertFalse(schedule.matches(datetime(2026, 11, 2, 0, 0)))  # day 2

    def test_star_and_restricted_combine_with_and(self) -> None:
        """FR-5: a star-started day field combines with AND, per Vixie cron."""
        schedule = parse("0 0 */5 * 1")
        self.assertTrue(schedule.matches(datetime(2026, 11, 16, 0, 0)))  # Monday, day 16
        self.assertFalse(schedule.matches(datetime(2026, 11, 2, 0, 0)))  # Monday, day 2
        self.assertFalse(schedule.matches(datetime(2026, 11, 6, 0, 0)))  # Friday, day 6

    def test_full_range_day_of_month_is_every_day(self) -> None:
        """FR-5: 1-31 restricted day-of-month matches every calendar day."""
        schedule = parse("0 0 1-31 * *")
        self.assertTrue(schedule.matches(datetime(2026, 11, 17, 0, 0)))


if __name__ == "__main__":
    unittest.main()
