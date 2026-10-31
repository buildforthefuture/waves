# Cronplain

Cronplain parses, validates, describes, and iterates standard five-field cron
expressions using nothing but the Python standard library. One small module
answers the three questions people actually have about a schedule: is this
expression valid, what does it mean, and when does it run next.

```python
>>> from cronplain import describe, parse
>>> describe("0 9 * * 1-5")
'At 09:00, on Monday through Friday.'
>>> schedule = parse("0 0 31 * *")
>>> schedule.next_after(datetime(2026, 2, 1, 10, 0))
datetime.datetime(2026, 3, 31, 0, 0)
```

## Why

Scheduling syntax outgrew Unix crontabs long ago; job runners, CI platforms,
and cloud schedulers all accept it. The Python ecosystem, however, splits the
work: runners compute times without explaining them, description libraries
carry dependencies and cannot compute runs, and shell validators report terse
errors. Cronplain does all three in about five hundred lines with zero
runtime dependencies, which keeps audits short and supply chains simple.

## Features

- Full five-field grammar: lists, ranges, steps, wildcards, `JAN`/`MON` names
- The seven time-based aliases (`@yearly`, `@monthly`, `@weekly`, `@daily`,
  `@midnight`, `@hourly`, `@annually`), with a clear rejection of `@reboot`
- Errors that name the offending field, such as `minute: value 60 out of range 0-59`
- The original Vixie day-field rule: day-of-month and day-of-week combine
  with either-or when both are restricted, and a field that starts with `*`
  intersects with the other
- Next and previous runs with day-level jumps, so month lengths, leap years,
  and weekends cost nothing; schedules that can never match fail fast with a
  clear message instead of looping
- A command-line interface: `describe`, `validate`, `next`, `prev`

## Installation

Cronplain has no runtime dependencies and supports Python 3.10 and later.

```sh
pip install .
```

## Library usage

```python
from datetime import datetime
from cronplain import CronError, describe, parse

print(describe("*/10 9-17 * * 1-5"))
# Every 10 minutes past every hour from 9 through 17, on Monday through Friday.

schedule = parse("0 0 1 * 1")   # the classic either-or surprise
schedule.matches(datetime(2026, 11, 2, 0, 0))    # Monday: True
schedule.matches(datetime(2026, 11, 3, 0, 0))    # Tuesday: False
print(schedule.next_after(datetime(2026, 10, 31, 12, 0)))

try:
    parse("60 * * * *")
except CronError as exc:
    print(exc)                   # minute: value 60 out of range 0-59
```

## Command-line usage

```sh
cronplain describe "0 */6 * * *"
cronplain validate "0 0 31 2 *" || echo "never matches"
cronplain next "*/15 * * * *" --count 3 --from 2026-11-01T09:50:00
cronplain prev "0 0 1 * *" --from 2026-03-15T00:00:00
```

## Semantics

Schedules operate on naive datetimes interpreted as wall-clock time, which is
how cron daemons treat a crontab. Callers holding timezone-aware datetimes
convert to the target zone first and pass the naive result. Expressions match
at minute granularity; seconds are ignored. Wrap-around ranges are rejected
rather than guessed at, and `0 0 31 2 *` — a schedule no calendar can satisfy
— raises a dedicated error instead of looping forever.

## Development

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -t .
ruff check src tests
mypy
```

The suite covers field grammar, alias expansion, day selection, iteration
around calendar edges, golden descriptions, and the CLI. Every requirement in
`SPEC.md` maps to at least one test.

## License

MIT — see `LICENSE`. Contributions follow `CONTRIBUTING.md`.
