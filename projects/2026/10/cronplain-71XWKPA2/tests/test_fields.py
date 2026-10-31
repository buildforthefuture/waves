"""Field grammar, error reporting, and safe parsing (FR-1, FR-3, FR-4, NFR-2)."""

from __future__ import annotations

import unittest

from cronplain.fields import parse_expression


class FieldGrammarTest(unittest.TestCase):
    """FR-1: lists, ranges, steps, wildcards, and names parse correctly."""

    def test_full_grammar(self) -> None:
        """FR-1: every field construct expands to its value set."""
        fields, alias = parse_expression("*/15 0,12 1-7 JAN-MAR *")
        self.assertEqual(sorted(fields[0][0]), [0, 15, 30, 45])
        self.assertEqual(sorted(fields[1][0]), [0, 12])
        self.assertEqual(sorted(fields[2][0]), [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(sorted(fields[3][0]), [1, 2, 3])
        self.assertEqual(sorted(fields[4][0]), [0, 1, 2, 3, 4, 5, 6])
        self.assertIsNone(alias)

    def test_step_after_single_value(self) -> None:
        """FR-1: a step after a single value spans to the field maximum."""
        fields, _ = parse_expression("5/15 * * * *")
        self.assertEqual(sorted(fields[0][0]), [5, 20, 35, 50])

    def test_range_with_step(self) -> None:
        """FR-1: a range with a step covers only the range."""
        fields, _ = parse_expression("10-30/10 * * * *")
        self.assertEqual(sorted(fields[0][0]), [10, 20, 30])


class WeekdayNormalizationTest(unittest.TestCase):
    """FR-4: 0 and 7 both mean Sunday; names are case-insensitive."""

    def test_zero_and_seven_are_sunday(self) -> None:
        """FR-4: 0 0 * * 0 and 0 0 * * 7 produce identical weekday sets."""
        zero, _ = parse_expression("0 0 * * 0")
        seven, _ = parse_expression("0 0 * * 7")
        self.assertEqual(zero[4][0], seven[4][0])
        self.assertEqual(sorted(zero[4][0]), [0])

    def test_name_case_insensitive(self) -> None:
        """FR-4: 0 0 * * sun matches 0 0 * * 0 and 0 0 * * SUN."""
        plain, _ = parse_expression("0 0 * * 0")
        for text in ("0 0 * * sun", "0 0 * * SUN", "0 0 * * Sun"):
            named, _ = parse_expression(text)
            self.assertEqual(plain[4][0], named[4][0])

    def test_month_names(self) -> None:
        """FR-4: month names normalize to numbers."""
        fields, _ = parse_expression("0 0 * JAN-MAR *")
        self.assertEqual(sorted(fields[3][0]), [1, 2, 3])


class ValidationErrorsTest(unittest.TestCase):
    """FR-3: every rejection names the field and the problem."""

    def _assert_field_error(self, expression: str, field: str) -> None:
        from cronplain.fields import CronError

        with self.assertRaises(CronError) as caught:
            parse_expression(expression)
        self.assertIn(field, str(caught.exception))
        self.assertEqual(caught.exception.field, field)

    def test_out_of_range_values(self) -> None:
        """FR-3: out-of-range values are rejected with the field name."""
        self._assert_field_error("60 * * * *", "minute")
        self._assert_field_error("* 24 * * *", "hour")
        self._assert_field_error("* * 0 * *", "day of month")
        self._assert_field_error("* * * 13 *", "month")
        self._assert_field_error("* * * * 8", "day of week")

    def test_unparseable_value(self) -> None:
        """FR-3: garbage values are rejected with the field name."""
        self._assert_field_error("x * * * *", "minute")
        self._assert_field_error("* * * FOO *", "month")

    def test_field_count(self) -> None:
        """FR-3: wrong field counts are rejected with guidance."""
        from cronplain.fields import CronError

        for text in ("* * *", "* * * * * *", ""):
            with self.assertRaises(CronError) as caught:
                parse_expression(text)
            self.assertIn("5 space-separated fields", str(caught.exception))

    def test_malformed_steps_and_ranges(self) -> None:
        """FR-3: zero steps, text steps, dangling separators are rejected."""
        from cronplain.fields import CronError

        for text in ("*/0 * * * *", "*/x * * * *", "1- * * * *", "*/ * * * *"):
            with self.assertRaises(CronError):
                parse_expression(text)

    def test_descending_range(self) -> None:
        """FR-3: wrap-around ranges are rejected explicitly."""
        from cronplain.fields import CronError

        with self.assertRaises(CronError) as caught:
            parse_expression("30-5 * * * *")
        self.assertIn("must ascend", str(caught.exception))

    def test_empty_list_entry(self) -> None:
        """FR-3: empty list entries are rejected."""
        from cronplain.fields import CronError

        with self.assertRaises(CronError):
            parse_expression("1,,2 * * * *")

    def test_alias_errors(self) -> None:
        """FR-3: unknown aliases are rejected listing the known set."""
        from cronplain.fields import CronError

        with self.assertRaises(CronError) as caught:
            parse_expression("@nope")
        self.assertIn("@daily", str(caught.exception))


class SafeParsingTest(unittest.TestCase):
    """NFR-2: untrusted input only ever raises CronError."""

    def test_corpus_of_malformed_input(self) -> None:
        """NFR-2: a corpus of garbage raises CronError and nothing else."""
        from cronplain.fields import CronError

        corpus = [
            "", "   ", "\t\n", "60 * * * *", "a * * * *", "* * *", "* * * * * *",
            "*/0 * * * *", "1-5-9 * * * *", "@", "@daily extra", "*/ * * * *",
            "*-1 * * * *", "1,,2 * * * *", "0 0 * L *", "0 0 * * SUN-SATDAY",
            "-5 * * * *", "5- * * * *", "1-/5 * * * *", "0 0 * JANUARY *",
        ]
        for text in corpus:
            with self.subTest(text=text):
                try:
                    parse_expression(text)
                except CronError:
                    pass
                except Exception as exc:  # noqa: BLE001 - the point of the test
                    self.fail(f"{text!r} raised {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    unittest.main()
