"""Command-line interface behavior (FR-9)."""

from __future__ import annotations

import contextlib
import io
import unittest

from cronplain.cli import main


class CliTest(unittest.TestCase):
    """FR-9: subcommands print useful output and fail with status 1."""

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_describe(self) -> None:
        """FR-9: describe prints the plain-English description."""
        code, out, _ = self._run(["describe", "*/15 * * * *"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "Every 15 minutes.\n")

    def test_validate(self) -> None:
        """FR-9: validate succeeds for a correct expression."""
        code, out, _ = self._run(["validate", "0 9 * * 1-5"])
        self.assertEqual(code, 0)
        self.assertIn("Monday", out)

    def test_next(self) -> None:
        """FR-9: next prints the requested number of ISO timestamps."""
        code, out, _ = self._run(
            ["next", "*/15 * * * *", "--count", "3", "--from", "2026-11-01T09:50:00"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            out,
            "2026-11-01T10:00:00\n2026-11-01T10:15:00\n2026-11-01T10:30:00\n",
        )

    def test_prev(self) -> None:
        """FR-9: prev prints matching times before the reference moment."""
        code, out, _ = self._run(
            ["prev", "0 0 1 * *", "--count", "2", "--from", "2026-03-15T00:00:00"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "2026-03-01T00:00:00\n2026-02-01T00:00:00\n")

    def test_invalid_expression_exits_nonzero(self) -> None:
        """FR-9: invalid input reports the error on stderr with status 1."""
        code, _, err = self._run(["describe", "60 * * * *"])
        self.assertEqual(code, 1)
        self.assertIn("error:", err)
        self.assertIn("minute", err)

    def test_never_matching_exits_nonzero(self) -> None:
        """FR-9: a schedule that never matches reports it with status 1."""
        code, _, err = self._run(["next", "0 0 31 2 *", "--from", "2026-01-01T00:00:00"])
        self.assertEqual(code, 1)
        self.assertIn("never matches", err)

    def test_bad_reference_datetime(self) -> None:
        """FR-9: a malformed reference datetime is rejected by the parser."""
        with self.assertRaises(SystemExit):
            self._run(["next", "* * * * *", "--from", "not-a-date"])

    def test_timezone_aware_reference_rejected(self) -> None:
        """FR-9: timezone-aware reference moments are rejected explicitly."""
        with self.assertRaises(SystemExit):
            self._run(["next", "* * * * *", "--from", "2026-11-01T09:00:00+02:00"])


if __name__ == "__main__":
    unittest.main()
