"""Plain-English rendering of a parsed schedule."""

from __future__ import annotations

from .schedule import Schedule

_WEEKDAYS = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
]
_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

_TIME_CAP = 4  # enumerate concrete clock times up to this many combinations


def _ordinal(number: int) -> str:
    if number % 100 in (11, 12, 13):
        return f"{number}th"
    if number % 10 == 1:
        return f"{number}st"
    if number % 10 == 2:
        return f"{number}nd"
    if number % 10 == 3:
        return f"{number}rd"
    return f"{number}th"


def _runs(values: tuple[int, ...]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for value in values:
        if runs and runs[-1][1] + 1 == value:
            runs[-1] = (runs[-1][0], value)
        else:
            runs.append((value, value))
    return runs


def _is_full(values: tuple[int, ...], low: int, high: int) -> bool:
    return len(values) == high - low + 1 and values[0] == low


def _step(values: tuple[int, ...], low: int, high: int) -> int | None:
    """Return the step when the values form the full range at a fixed stride."""
    if len(values) < 2 or values[0] != low or values[-1] > high:
        return None
    step = values[1] - values[0]
    if step < 2:
        return None
    expected = list(range(low, high + 1, step))
    return step if list(values) == expected else None


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _list_phrase(
    values: tuple[int, ...],
    labels: list[str],
    prefix: str,
    full_text: str,
    offset: int = 0,
) -> str | None:
    """Render a value set as a phrase such as 'on Monday through Friday'."""
    if _is_full(values, offset, offset + len(labels) - 1):
        return full_text
    items: list[str] = []
    for start, end in _runs(values):
        if start == end:
            items.append(labels[start - offset])
        else:
            items.append(f"{labels[start - offset]} through {labels[end - offset]}")
    return f"{prefix} {_join(items)}"


def _dom_phrase(values: tuple[int, ...]) -> str | None:
    if _is_full(values, 1, 31):
        return None
    step = _step(values, 1, 31)
    if step is not None:
        return f"on every {_ordinal(step)} day of the month"
    runs = _runs(values)
    if len(runs) == 1:
        start, end = runs[0]
        if start == end:
            return f"on day {start} of the month"
        return f"on day {start} through {end} of the month"
    items = [
        f"{start} through {end}" if start != end else f"{start}" for start, end in runs
    ]
    return f"on days {_join(items)} of the month"


def _dow_phrase(values: tuple[int, ...]) -> str | None:
    if _is_full(values, 0, 6):
        return None
    return _list_phrase(values, _WEEKDAYS, "on", "every day of the week")


def _month_phrase(values: tuple[int, ...]) -> str | None:
    if _is_full(values, 1, 12):
        return None
    return _list_phrase(values, _MONTHS, "in", "every month", offset=1)


def _minute_phrase(values: tuple[int, ...]) -> str:
    step = _step(values, 0, 59)
    if step is not None:
        return f"every {step} minutes"
    runs = _runs(values)
    if len(runs) == 1:
        start, end = runs[0]
        return f"minute {start}" if start == end else f"minute {start} through {end}"
    items = [f"{start} through {end}" if start != end else f"{start}" for start, end in runs]
    return f"minutes {_join(items)}"


def _hour_phrase(values: tuple[int, ...]) -> str:
    step = _step(values, 0, 23)
    if step is not None:
        return f"every {_ordinal(step)} hour"
    runs = _runs(values)
    if len(runs) == 1:
        start, end = runs[0]
        if start == end:
            return f"hour {start}"
        return f"every hour from {start} through {end}"
    items = [f"{start} through {end}" if start != end else f"{start}" for start, end in runs]
    return f"hours {_join(items)}"


def _time_phrase(minutes: tuple[int, ...], hours: tuple[int, ...]) -> str:
    if _is_full(minutes, 0, 59) and _is_full(hours, 0, 23):
        return "Every minute"
    if _is_full(hours, 0, 23):
        step = _step(minutes, 0, 59)
        if step is not None:
            return f"Every {step} minutes"
        return f"At {_minute_phrase(minutes)} past every hour"
    if _is_full(minutes, 0, 59):
        step = _step(hours, 0, 23)
        if step is not None:
            return f"Every minute past every {_ordinal(step)} hour"
        return f"Every minute past {_hour_phrase(hours)}"
    if len(minutes) * len(hours) <= _TIME_CAP:
        times = [f"{hour:02d}:{minute:02d}" for hour in hours for minute in minutes]
        return f"At {_join(times)}"
    minute_part = _minute_phrase(minutes)
    hour_part = _hour_phrase(hours)
    if minute_part.startswith("every "):
        return f"{minute_part[0].upper()}{minute_part[1:]} past {hour_part}"
    return f"At {minute_part} past {hour_part}"


def _strip_on(phrase: str) -> str:
    return phrase[3:] if phrase.startswith("on ") else phrase


def _day_phrase(
    days_of_month: tuple[int, ...],
    dom_star: bool,
    days_of_week: tuple[int, ...],
    dow_star: bool,
) -> str | None:
    dom = _dom_phrase(days_of_month)
    dow = _dow_phrase(days_of_week)
    if dom_star or dow_star:
        # Both day fields combine with AND when either starts with '*'.
        if dom is None and dow is None:
            return None
        if dom is None:
            return dow
        if dow is None:
            return dom
        return f"{dom} that is also {_strip_on(dow)}"
    # Neither field starts with '*': the original either-or rule applies.
    if dom is None or dow is None:
        return None
    return f"{dom} or {dow}"


def describe_schedule(schedule: Schedule) -> str:
    """Return a deterministic plain-English description."""
    minutes = schedule.minutes
    hours = schedule.hours
    days_of_month = schedule.days_of_month
    months = schedule.months
    days_of_week = schedule.days_of_week

    parts = [_time_phrase(minutes, hours)]
    day = _day_phrase(days_of_month, schedule.dom_star, days_of_week, schedule.dow_star)
    if day is not None:
        parts.append(day)
    month = _month_phrase(months)
    if month is not None:
        parts.append(month)
    sentence = ", ".join(parts) + "."
    return sentence[0].upper() + sentence[1:]
