"""Bond cash flows, present value and Treasury-curve helpers (Drew, Week 2).

Conventions:
    coupon: Annual rate in percent (5 means 5%), as in the bond table.
    yields and spreads: Decimals (0.0488 means 4.88%).
    time: Years.
    face: Defaults to 100.
"""

import sys
from datetime import date, datetime
from functools import lru_cache
from numbers import Real
from pathlib import Path

import numpy as np
import pandas as pd

# fred_api.py lives in src, next to this file
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fred_api import get_latest


def load_bonds(csv):
    """Read the finance team's bond table.

    Expected columns: Issuer, CUSIP, Coupon (%), Maturity Date, Price, Rating.

    Args:
        csv: Path to the CSV file.

    Returns:
        A DataFrame with `Maturity Date` parsed to `datetime.date` so the other
        functions can use it.
    """
    bonds = pd.read_csv(csv)
    bonds.columns = bonds.columns.str.strip()
    # normilize the date format
    bonds["Maturity Date"] = pd.to_datetime(bonds["Maturity Date"]).dt.date
    return bonds


def _to_date(d):
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


def _shift_years(d, n):
    """Return `d` moved by `n` calendar years (negative goes back).

    Feb 29 falls back to Feb 28 in a non-leap year.
    """
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def years_to_maturity(maturity_date, today=None):
    """Return the exact calendar years from `today` to a maturity date.

    Whole years are counted back from maturity (2026-11-10 to 2031-11-10 is
    exactly 5.0); the leftover days are divided by the length (365 or 366) of
    the year they fall in. This is the same anchor-on-maturity logic as
    cash_flows() and is close to the actual/actual convention used for Treasuries.

    Args:
        maturity_date: A date, datetime, Timestamp or "YYYY-MM-DD" string.
        today: Reference date in the same formats. Defaults to the current date.

    Returns:
        Years remaining, as a float.

    Raises:
        ValueError: If the bond matured before `today`.
    """
    today = date.today() if today is None else _to_date(today)
    maturity = _to_date(maturity_date)
    if maturity < today:
        raise ValueError(f"Bond matured {(today - maturity).days} days before {today}.")

    whole = maturity.year - today.year
    while _shift_years(maturity, -whole) < today:  # step back until the anniversary is on/after today
        whole -= 1
    anniversary = _shift_years(maturity, -whole)  # first anniversary of maturity on/after today
    year_before = _shift_years(maturity, -(whole + 1))
    stub = (anniversary - today).days / (anniversary - year_before).days
    return whole + stub


def cash_flows(coupon, maturity, face: float | None = 100.0, today=None, freq=2):
    """Return a bond's remaining payments, soonest first.

    Coupon dates are counted back from maturity in 1/freq-year steps, so the
    first coupon can fall less than 1/freq years from today. The last payment
    includes the principal.

    Args:
        coupon: Annual coupon rate in percent (5 means 5%).
        maturity: Years left as a number, or a maturity date ("YYYY-MM-DD",
            date, datetime or Timestamp) converted with years_to_maturity.
        face: Face value; amounts are per `face`. None is treated as 0.
        today: Reference date, used only when `maturity` is a date.
        freq: Coupons per year (1 annual, 2 semiannual, 4 quarterly, 12 monthly).

    Returns:
        A DataFrame with columns `years` (time to each payment) and
        `cash_flow` (amount paid, in the units of `face`).

    Raises:
        ValueError: If `maturity` is a date in the past.

    Note:
        The first payment is a full coupon with no accrued interest removed, so
        present_value() of these flows is the dirty price between coupon dates.

    Example:
        cash_flows(5, 2) pays 2.5 at 0.5, 1.0 and 1.5 years and 102.5 at 2.0.
    """
    if face is None:
        face = 0

    # Real, not int/float, so numpy numbers (np.int64) count as years, not dates.
    years = maturity if isinstance(maturity, Real) else years_to_maturity(maturity, today)
    step = 1 / freq

    # Round first so float noise (10.0 * 2 = 19.999...) does not add a payment.
    n = int(np.ceil(round(years * freq, 9)))
    n = max(n, 1)  # years=0 still pays the last coupon and principal

    # Count back from maturity, e.g. 4.8 years: 4.8, 4.3, ..., 0.3 (next coupon).
    times = years - step * np.arange(n)[::-1]
    flows = np.full(n, face * coupon / 100 / freq)
    flows[-1] += face  # principal is repaid with the last coupon

    return pd.DataFrame({"years": times, "cash_flow": flows})


def present_value(cf, ytm, compounding=2):
    """Discount cash flows to today and sum them: the bond's dirty price.

    Args:
        cf: DataFrame from cash_flows() with `years` and `cash_flow` columns.
        ytm: Yield as a decimal (0.05 means 5%).
        compounding: Yield compounding per year (1 annual, 2 semiannual,
            4 quarterly, 12 monthly) or "continuous". This is separate from the
            coupon frequency set by cash_flows(freq=...).

    Returns:
        Present value as a float. Discrete compounding is
        sum(CF * (1 + y/m) ** (-m * t)); continuous is sum(CF * exp(-y * t)).
        The same yield gives a lower price with continuous compounding; to match
        prices, convert with r_cont = m * ln(1 + y/m).

    Raises:
        ValueError: If `compounding` is not a positive number or "continuous".
    """
    t = cf["years"].to_numpy(dtype=float)
    flows = cf["cash_flow"].to_numpy(dtype=float)

    if compounding == "continuous":
        factors = np.exp(-ytm * t)  # limit of (1 + y/m)^(-m t) as m -> infinity
    elif isinstance(compounding, Real) and compounding > 0:
        factors = (1 + ytm / compounding) ** (-compounding * t)
    else:
        raise ValueError(f'compounding must be a positive number or "continuous", got {compounding!r}')

    return float((flows * factors).sum())


TENORS = {5: "DGS5", 7: "DGS7", 10: "DGS10"}


def treasury_curve():
    """Return the latest 5/7/10-year Treasury yields from FRED.

    Fetches the last 10 prints of each series in TENORS and keeps the latest
    date on which all three exist. Every call hits FRED (3 requests); nothing is
    cached.

    Returns:
        A Series of decimal yields indexed by tenor in years (5, 7, 10). The
        date is stored in `.attrs["as_of"]`.

    Raises:
        RuntimeError: If none of the 10 dates has all three yields.
    """
    data = pd.concat({t: get_latest(sid, n=10) for t, sid in TENORS.items()}, axis=1).dropna()
    if data.empty:
        raise RuntimeError("No date in the last 10 FRED prints has all of DGS5, DGS7, DGS10.")
    latest = data.iloc[-1] / 100  # FRED quotes percent
    latest.attrs["as_of"] = data.index[-1].date()
    return latest


def treasury_yield(years):
    """Return the Treasury yield at `years`, linearly interpolated.

    Uses the 5/7/10-year yields from treasury_curve(), all from the same date.
    Outside 5-10 years it holds the end value flat and prints a warning; add
    DGS2/DGS3/DGS20 if a wider range is needed. Each call makes 3 FRED requests.

    Args:
        years: Maturity in years.

    Returns:
        The interpolated yield as a decimal.
    """
    curve = treasury_curve()
    lo, hi = curve.index.min(), curve.index.max()
    if not lo <= years <= hi:
        print(f"Warning: {years:.2f}y is outside {lo}-{hi}y; using flat extrapolation.")
    return float(np.interp(years, curve.index, curve.values))


def spread(bond_yield, years):
    """Return the bond's yield minus the Treasury yield at the same maturity.

    Args:
        bond_yield: The bond's yield as a decimal (e.g. from Brian's ytm()).
        years: The bond's years to maturity.

    Returns:
        The spread as a decimal; multiply by 10,000 for basis points.
    """
    return bond_yield - treasury_yield(years)
