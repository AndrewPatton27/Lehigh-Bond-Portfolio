"""Date helpers: parsing, year shifts, years between two dates and years to maturity."""

from datetime import date, datetime
from typing import TypeAlias

import numpy as np
import pandas as pd

DateLike: TypeAlias = str | date | datetime | pd.Timestamp | np.datetime64

def years_between(start: DateLike, end: DateLike) -> float:
    """Return the exact calendar years from `start` to `end`.

    Whole years are counted back from `end` (2026-11-10 to 2031-11-10 is exactly
    5.0); the leftover days are divided by the length (365 or 366) of the year
    they fall in. This is the same anchor-on-maturity logic as cash_flows() and is
    close to the actual/actual convention used for Treasuries.

    Args:
        start: A date, datetime, Timestamp, numpy datetime64 or "YYYY-MM-DD" string.
        end: A date in the same formats.

    Returns:
        Years from `start` to `end`. Positive if `end` is after `start`, negative
        if `end` has already passed, and 0.0 if they are the same day.
    """
    start_date = _to_date(start)
    end_date = _to_date(end)
    if end_date < start_date:
        return -years_between(end_date, start_date)

    whole = end_date.year - start_date.year
    while _shift_years(end_date, -whole) < start_date:  # step back until the anniversary is on/after start
        whole -= 1
    anniversary = _shift_years(end_date, -whole)  # first anniversary of `end` on/after start
    year_before = _shift_years(end_date, -(whole + 1))
    stub = (anniversary - start_date).days / (anniversary - year_before).days
    return whole + stub


def years_to_maturity(maturity_date: DateLike, today: DateLike | None = None) -> float:
    """Return the exact calendar years from `today` to a maturity date.

    Args:
        maturity_date: A date, datetime, Timestamp or "YYYY-MM-DD" string.
        today: Reference date in the same formats. Defaults to the current date.

    Returns:
        Years remaining, as a float. See years_between().

    Raises:
        ValueError: If the bond matured before `today`.
    """
    today_date = date.today() if today is None else _to_date(today)
    maturity = _to_date(maturity_date)
    if maturity < today_date:
        raise ValueError(f"Bond matured {(today_date - maturity).days} days before {today_date}.")
    return years_between(today_date, maturity)


def _to_date(d: DateLike) -> date:
    """Convert a date-like value to a plain `datetime.date`.

    Accepts a "YYYY-MM-DD" string, date, datetime, pandas Timestamp or numpy
    datetime64. `datetime` is checked before `date` because it subclasses it.
    """
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    if isinstance(d, datetime):  # check datetime first: datetime is a subclass of date
        return d.date()
    if isinstance(d, date):
        return d
    return pd.Timestamp(d).date()  # pandas Timestamp, numpy datetime64


def _shift_years(d: date, n: int) -> date:
    """Return `d` moved by `n` calendar years (negative goes back).

    Feb 29 falls back to Feb 28 in a non-leap year.
    """
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)
