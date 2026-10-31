"""Field parsing for standard five-field cron expressions."""

from __future__ import annotations

MINUTE_RANGE = (0, 59)
HOUR_RANGE = (0, 23)
DAY_OF_MONTH_RANGE = (1, 31)
MONTH_RANGE = (1, 12)
DAY_OF_WEEK_RANGE = (0, 7)

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
DAY_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}

FIELD_NAMES = ("minute", "hour", "day of month", "month", "day of week")
FIELD_RANGES = (
    MINUTE_RANGE,
    HOUR_RANGE,
    DAY_OF_MONTH_RANGE,
    MONTH_RANGE,
    DAY_OF_WEEK_RANGE,
)
FIELD_NAME_MAPS = (None, None, None, MONTH_NAMES, DAY_NAMES)


class CronError(ValueError):
    """Raised when a cron expression cannot be parsed or never matches."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message)


class NoMatchError(CronError):
    """Raised when a schedule matches no calendar date."""


def _value(text: str, index: int) -> int:
    low, high = FIELD_RANGES[index]
    name = FIELD_NAMES[index]
    names = FIELD_NAME_MAPS[index]
    token = text.strip()
    if not token:
        raise CronError(f"{name}: empty value", name)
    if names is not None and token.lower() in names:
        return names[token.lower()]
    if not token.isdigit():
        raise CronError(f"{name}: cannot parse value {text!r}", name)
    value = int(token)
    if value < low or value > high:
        raise CronError(f"{name}: value {value} out of range {low}-{high}", name)
    return value


def parse_field(text: str, index: int) -> tuple[frozenset[int], bool]:
    """Parse one field into its value set.

    Returns the values plus a flag telling whether the field text starts
    with ``*``. That flag drives the day-of-month/day-of-week combination
    rule, which follows the original Vixie cron documentation: the either-or
    rule applies only when neither field starts with ``*``.
    """
    name = FIELD_NAMES[index]
    low, high = FIELD_RANGES[index]
    values: set[int] = set()
    star = text.startswith("*")
    if not text.strip():
        raise CronError(f"{name}: field is empty", name)
    for part in text.split(","):
        if not part:
            raise CronError(f"{name}: empty list entry in {text!r}", name)
        if part.endswith("/"):
            raise CronError(f"{name}: step requires a value in {part!r}", name)
        base, _, step_text = part.partition("/")
        step = 1
        if step_text:
            if not step_text.isdigit() or int(step_text) == 0:
                raise CronError(
                    f"{name}: step must be a positive integer, got {step_text!r}", name
                )
            step = int(step_text)
        if base == "":
            raise CronError(f"{name}: cannot parse value {part!r}", name)
        if base == "*":
            values.update(range(low, high + 1, step))
            continue
        if "-" in base:
            start_text, _, end_text = base.partition("-")
            start = _value(start_text, index)
            end = _value(end_text, index)
            if start > end:
                raise CronError(
                    f"{name}: range {base!r} must ascend; wrap-around ranges are not supported",
                    name,
                )
            values.update(range(start, end + 1, step))
            continue
        start = _value(base, index)
        if step_text:
            values.update(range(start, high + 1, step))
        else:
            values.add(start)
    if index == 4:
        values = {0 if value == 7 else value for value in values}
    return frozenset(values), star


ALIAS_EXPANSIONS: dict[str, str] = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}


def parse_expression(
    text: str,
) -> tuple[list[tuple[frozenset[int], bool]], str | None]:
    """Parse a full expression into five ``(values, star)`` field tuples.

    The second element of the result names the alias the expression came
    from, or ``None`` for a plain five-field expression.
    """
    stripped = text.strip()
    lowered = stripped.lower()
    alias: str | None = None
    if lowered.startswith("@"):
        if lowered in ALIAS_EXPANSIONS:
            alias = lowered
            stripped = ALIAS_EXPANSIONS[lowered]
        elif lowered == "@reboot":
            raise CronError(
                "@reboot is not time-based; it runs once when the scheduler starts"
            )
        else:
            known = ", ".join(sorted(ALIAS_EXPANSIONS))
            raise CronError(f"unknown alias {lowered!r}; known aliases: {known}")
    parts = stripped.split()
    if len(parts) != 5:
        raise CronError(
            "expected 5 space-separated fields (minute, hour, day of month, "
            f"month, day of week), got {len(parts)} in {text!r}"
        )
    try:
        fields = [parse_field(part, index) for index, part in enumerate(parts)]
    except CronError:
        raise
    except Exception as exc:  # pragma: no cover - defensive, keeps parsing safe
        raise CronError(f"unexpected parse failure: {exc}") from exc
    return fields, alias
