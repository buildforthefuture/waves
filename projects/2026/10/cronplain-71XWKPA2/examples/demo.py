"""Demonstrate cronplain on a handful of everyday schedules.

Run with: PYTHONPATH=src python3 examples/demo.py
"""

from __future__ import annotations

from datetime import datetime

from cronplain import CronError, describe, parse

SAMPLES = [
    "*/15 * * * *",
    "0 9 * * 1-5",
    "0 */6 * * *",
    "0 0 1 * 1",
    "0 0 29 2 *",
    "@daily",
]

REFERENCE = datetime(2026, 11, 1, 12, 0)

for expression in SAMPLES:
    print(f"{expression!r}: {describe(expression)}")
    schedule = parse(expression)
    upcoming = schedule.next_n(REFERENCE, 3)
    rendered = ", ".join(moment.isoformat(sep=" ") for moment in upcoming)
    print(f"    next three after {REFERENCE:%Y-%m-%d %H:%M}: {rendered}")

try:
    parse("0 0 31 2 *").next_after(REFERENCE)
except CronError as exc:
    print(f"0 0 31 2 *: {exc}")
