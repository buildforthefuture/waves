"""cronplain: parse, describe, and iterate standard five-field cron expressions.

Pure standard library. Schedules operate on naive datetimes treated as
wall-clock time, matching how cron daemons interpret a crontab.
"""

from .describe import describe_schedule
from .fields import CronError, NoMatchError
from .schedule import Schedule, parse

__all__ = [
    "CronError",
    "NoMatchError",
    "Schedule",
    "describe",
    "describe_schedule",
    "parse",
]

__version__ = "0.1.0"


def describe(expression: str) -> str:
    """Parse an expression and return its plain-English description."""
    return describe_schedule(parse(expression))
