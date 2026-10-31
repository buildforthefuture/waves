"""Schedule matching and iteration over wall-clock time."""

from __future__ import annotations

from datetime import datetime, timedelta

from .fields import NoMatchError, parse_expression

_JUMP_LIMIT = 12 * 367  # twelve years of day jumps covers every real cycle


def _weekday(dt: datetime) -> int:
    """Return the cron weekday: 0 is Sunday, 6 is Saturday."""
    return (dt.weekday() + 1) % 7


class Schedule:
    """A parsed, immutable cron schedule.

    All matching happens on naive datetimes interpreted as wall-clock time,
    which is how cron daemons treat a crontab. Callers working with
    timezone-aware datetimes convert to the target zone first and pass the
    naive result.
    """

    __slots__ = (
        "expression",
        "alias",
        "_minutes",
        "_hours",
        "_days_of_month",
        "_months",
        "_days_of_week",
        "_dom_star",
        "_dow_star",
    )

    def __init__(
        self,
        expression: str,
        alias: str | None,
        fields: list[tuple[frozenset[int], bool]],
    ) -> None:
        self.expression = expression
        self.alias = alias
        (self._minutes, _), (self._hours, _) = fields[0], fields[1]
        (self._days_of_month, self._dom_star) = fields[2]
        (self._months, _) = fields[3]
        (self._days_of_week, self._dow_star) = fields[4]

    @property
    def minutes(self) -> tuple[int, ...]:
        return tuple(sorted(self._minutes))

    @property
    def hours(self) -> tuple[int, ...]:
        return tuple(sorted(self._hours))

    @property
    def days_of_month(self) -> tuple[int, ...]:
        return tuple(sorted(self._days_of_month))

    @property
    def months(self) -> tuple[int, ...]:
        return tuple(sorted(self._months))

    @property
    def days_of_week(self) -> tuple[int, ...]:
        return tuple(sorted(self._days_of_week))

    @property
    def dom_star(self) -> bool:
        return self._dom_star

    @property
    def dow_star(self) -> bool:
        return self._dow_star

    def _day_matches(self, dt: datetime) -> bool:
        if self._dom_star or self._dow_star:
            return dt.day in self._days_of_month and _weekday(dt) in self._days_of_week
        return dt.day in self._days_of_month or _weekday(dt) in self._days_of_week

    def matches(self, dt: datetime) -> bool:
        """Return whether this schedule fires during the minute of ``dt``.

        Seconds and microseconds are ignored, matching cron's minute
        granularity.
        """
        return (
            dt.minute in self._minutes
            and dt.hour in self._hours
            and dt.month in self._months
            and self._day_matches(dt)
        )

    def _first_of_next_allowed_month(self, dt: datetime) -> datetime:
        year, month = dt.year, dt.month
        for _ in range(13):
            month += 1
            if month > 12:
                month = 1
                year += 1
            if month in self._months:
                return datetime(year, month, 1)
        raise NoMatchError("the schedule never matches any calendar date")

    def _first_of_previous_allowed_month(self, dt: datetime) -> datetime:
        year, month = dt.year, dt.month
        for _ in range(13):
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            if month in self._months:
                if month == 12:
                    next_first = datetime(year + 1, 1, 1)
                else:
                    next_first = datetime(year, month + 1, 1)
                return next_first - timedelta(minutes=1)
        raise NoMatchError("the schedule never matches any calendar date")

    def next_after(self, dt: datetime) -> datetime:
        """Return the first matching time strictly after ``dt``.

        Raises :class:`NoMatchError` when no calendar date can ever match,
        for example ``0 0 31 2 *``.
        """
        t = dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
        jumps = 0
        while jumps <= _JUMP_LIMIT:
            if t.month not in self._months:
                t = self._first_of_next_allowed_month(t)
                jumps += 1
                continue
            if not self._day_matches(t):
                t = datetime(t.year, t.month, t.day) + timedelta(days=1)
                jumps += 1
                continue
            if t.hour not in self._hours:
                later = [hour for hour in self.hours if hour > t.hour]
                if later:
                    t = t.replace(hour=later[0], minute=self.minutes[0])
                else:
                    t = datetime(t.year, t.month, t.day) + timedelta(days=1)
                    jumps += 1
                continue
            if t.minute not in self._minutes:
                later = [minute for minute in self.minutes if minute > t.minute]
                if later:
                    t = t.replace(minute=later[0])
                elif t.hour == 23:
                    t = datetime(t.year, t.month, t.day) + timedelta(days=1)
                    jumps += 1
                else:
                    t = t.replace(hour=t.hour + 1, minute=self.minutes[0])
                continue
            return t
        raise NoMatchError("the schedule never matches any calendar date")

    def previous_before(self, dt: datetime) -> datetime:
        """Return the last matching time strictly before ``dt``."""
        t = dt.replace(second=0, microsecond=0)
        if dt.second or dt.microsecond:
            if self.matches(t):
                return t
        t -= timedelta(minutes=1)
        jumps = 0
        while jumps <= _JUMP_LIMIT:
            if t.year < 2:
                raise NoMatchError("the schedule matches nothing this far back")
            if t.month not in self._months:
                t = self._first_of_previous_allowed_month(t)
                jumps += 1
                continue
            if not self._day_matches(t):
                t = datetime(t.year, t.month, t.day) - timedelta(minutes=1)
                jumps += 1
                continue
            if t.hour not in self._hours:
                earlier = [hour for hour in self.hours if hour < t.hour]
                if earlier:
                    t = t.replace(hour=earlier[-1], minute=self.minutes[-1])
                else:
                    t = datetime(t.year, t.month, t.day) - timedelta(minutes=1)
                    jumps += 1
                continue
            if t.minute not in self._minutes:
                earlier = [minute for minute in self.minutes if minute < t.minute]
                if earlier:
                    t = t.replace(minute=earlier[-1])
                elif t.hour == 0:
                    t = datetime(t.year, t.month, t.day) - timedelta(minutes=1)
                    jumps += 1
                else:
                    t = t.replace(hour=t.hour - 1, minute=self.minutes[-1])
                continue
            return t
        raise NoMatchError("the schedule never matches any calendar date")

    def next_n(self, dt: datetime, count: int) -> list[datetime]:
        """Return up to ``count`` matching times strictly after ``dt``."""
        if count < 1:
            raise ValueError("count must be at least 1")
        found: list[datetime] = []
        cursor = dt
        while len(found) < count:
            cursor = self.next_after(cursor)
            found.append(cursor)
        return found

    def __repr__(self) -> str:
        source = self.alias or self.expression
        return f"Schedule({source!r})"


def parse(text: str) -> Schedule:
    """Parse a standard five-field expression or ``@`` alias."""
    fields, alias = parse_expression(text)
    return Schedule(text, alias, fields)
