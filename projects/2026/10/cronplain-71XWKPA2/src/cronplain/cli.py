"""Command-line interface for cronplain."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .describe import describe_schedule
from .fields import CronError
from .schedule import parse


def _when(text: str) -> datetime:
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid datetime {text!r}; use ISO 8601 such as 2026-11-01T09:00:00"
        ) from None
    if moment.tzinfo is not None:
        raise argparse.ArgumentTypeError(
            "provide a naive local time without a timezone offset"
        )
    return moment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronplain",
        description="Explain and iterate standard five-field cron expressions.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("describe", "print a plain-English description"),
        ("validate", "parse an expression and print its description on success"),
    ):
        one = sub.add_parser(name, help=help_text)
        one.add_argument("expression", help="five-field expression or @alias")

    for name, help_text in (
        ("next", "print matching times after a reference moment"),
        ("prev", "print matching times before a reference moment"),
    ):
        many = sub.add_parser(name, help=help_text)
        many.add_argument("expression", help="five-field expression or @alias")
        many.add_argument("--count", type=int, default=1, help="how many times")
        many.add_argument(
            "--from",
            dest="when",
            type=_when,
            default=datetime.now().replace(second=0, microsecond=0),
            help="naive ISO datetime to search from (default: now)",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        schedule = parse(args.expression)
        if args.command in ("describe", "validate"):
            print(describe_schedule(schedule))
            return 0
        moment = args.when
        for _ in range(max(args.count, 1)):
            if args.command == "next":
                moment = schedule.next_after(moment)
            else:
                moment = schedule.previous_before(moment)
            print(moment.isoformat())
        return 0
    except CronError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
