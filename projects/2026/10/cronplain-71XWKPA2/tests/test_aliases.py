"""Alias handling (FR-2)."""

from __future__ import annotations

import unittest

from cronplain.fields import ALIAS_EXPANSIONS, CronError, parse_expression
from cronplain.schedule import parse


class AliasTest(unittest.TestCase):
    """FR-2: the eight time-based aliases behave as their equivalents."""

    def test_aliases_expand(self) -> None:
        """FR-2: every alias parses to the same fields as its expansion."""
        for alias, expansion in ALIAS_EXPANSIONS.items():
            with self.subTest(alias=alias):
                from_alias, name = parse_expression(alias)
                from_plain, _ = parse_expression(expansion)
                self.assertEqual(name, alias)
                pairs = zip(from_alias, from_plain, strict=True)
                for (values_a, star_a), (values_b, star_b) in pairs:
                    self.assertEqual(values_a, values_b)
                    self.assertEqual(star_a, star_b)

    def test_alias_case_insensitive(self) -> None:
        """FR-2: @DAILY is accepted like @daily."""
        _, name = parse_expression("@DAILY")
        self.assertEqual(name, "@daily")

    def test_reboot_rejected(self) -> None:
        """FR-2: @reboot is rejected with an explanation."""
        with self.assertRaises(CronError) as caught:
            parse_expression("@reboot")
        self.assertIn("not time-based", str(caught.exception))

    def test_schedule_remembers_alias(self) -> None:
        """FR-2: a parsed schedule records the alias it came from."""
        schedule = parse("@hourly")
        self.assertEqual(schedule.alias, "@hourly")
        self.assertEqual(schedule.minutes, (0,))


if __name__ == "__main__":
    unittest.main()
