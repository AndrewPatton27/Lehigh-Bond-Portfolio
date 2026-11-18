"""Data and cash flows (Drew, Week 2).

**Conventions**:
- `coupon` is in **percent** (5 = 5%), matching the bond table's `Coupon (%)` column.
- Yields and spreads are **decimals** (0.0488 = 4.88%)
- Time is in **years**
- Face defaults to 100.
"""

import sys
from datetime import date, datetime
from functools import lru_cache
from numbers import Real
from pathlib import Path

import numpy as np
import pandas as pd

# fred_api.py lives in src/bondhedge, next to this file
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fred_api import get_latest


def load_bonds(csv):
    """Reads the finance students' bond table.
    format: Issuer | CUSIP | Coupon (%) | Maturity Date | Price | Rating
    csv is the path to the csv file. Maturity is parsed to a date so the other functions can use it.
    """
    bonds = pd.read_csv(csv)
    bonds.columns = bonds.columns.str.strip()
    # normilize the date format
    bonds["Maturity Date"] = pd.to_datetime(bonds["Maturity Date"]).dt.date
    return bonds


def _to_date(d):
    """Helper. Turns a `"YYYY-MM-DD"` string, `date`, `datetime`, pandas `Timestamp` or numpy `datetime64` into a plain `date`.
    `datetime` is checked before `date` because `datetime` is a subclass of `date`.
    """
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    if isinstance(d, datetime):  # check datetime first: datetime is a subclass of date
        return d.date()
    if isinstance(d, date):
        return d
    return pd.Timestamp(d).date()  # pandas Timestamp, numpy datetime64


def _shift_years(d, n):
    """d moved n calendar years. Feb 29 falls back to Feb 28 in non-leap years.

    Helper. Moves date `d` by `n` calendar years (negative `n` goes back).
    Feb 29 becomes Feb 28 in a non-leap year.
    """
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def years_to_maturity(maturity_date, today=None):
    """Exact calendar years left: whole years counted back from maturity, plus the
    leftover days divided by the true length (365 or 366) of the year they fall in.

    Converts a date into years with an exact calendar count, not days / 365.25.
    Whole years are counted back from maturity (so 2026-11-10 to 2031-11-10 is exactly 5.0). The leftover days are
    divided by the actual length of the year they fall in (365 or 366). This is the same anchor-on-maturity logic as
    `cash_flows`, close to the actual/actual convention used for Treasuries.
    Accepts dates, datetimes or `"YYYY-MM-DD"` strings. `today` defaults to the current date.
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
    """Lists every payment the bond still has left: each coupon, plus the face value repaid with the last coupon.
    Returns a DataFrame, soonest payment first:
    - `years`: time from today until the payment, in years
    - `cash_flow`: amount paid (in the same units as `face`)

    **Arguments**
    - `coupon`: annual coupon rate in **percent** (5 = 5%), as in the bond table's `Coupon (%)` column.
    - `maturity`: years left as a number (`4.8`, `10`, or a numpy number like `np.int64(10)`), or a maturity date
      (`"YYYY-MM-DD"`, `date`, `datetime`, `Timestamp`), which is turned into years with `years_to_maturity(maturity, today)`.
    - `face`: face value, default 100, so amounts are per 100 of face like bond price quotes. `None` is treated as 0, which makes every cash flow 0.
    - `today`: only used when `maturity` is a date. Defaults to today's date.
    - `freq`: coupons per year: 1 = annual, 2 = semiannual (US default), 4 = quarterly, 12 = monthly.
      Each coupon is `face * coupon / 100 / freq`, and payments are `1 / freq` years apart.

    **How the schedule is built**
    Coupon dates are set by the maturity date, not by today, so payments are counted **back from maturity** in `1 / freq`-year steps.
    With 4.8 years left and semiannual coupons: 4.8, 4.3, ..., 0.8, 0.3. The first coupon is in 0.3 years, not 0.5.
    - Number of payments = `ceil(years * freq)`, rounded to 9 decimals first so float noise (10.0 * 2 = 19.999...) doesn't add a payment.
    - Maturing today (0 years left) gives one row at `years=0`: the last coupon plus principal.

    **Example:** `cash_flows(5, 2)`, a 5% bond with 2 years left, semiannual:

    | years | cash_flow |
    |---|---|
    | 0.5 | 2.5 |
    | 1.0 | 2.5 |
    | 1.5 | 2.5 |
    | 2.0 | 102.5 |

    **Limits**
    - The first payment is always a full coupon; accrued interest is not subtracted. So `present_value(cash_flows(...), ytm)` gives the **dirty** price for a bond between coupon dates (clean price = dirty - accrued).
    - A maturity date in the past raises `ValueError`. `freq=0` raises `ZeroDivisionError`.
    - `cash_flows` only lists payments; discounting them to a price is `present_value` below.
    """
    if face == None:
        face = 0

    # Real (not int/float) so numpy numbers like np.int64 from a DataFrame count as years, not dates
    years = maturity if isinstance(maturity, Real) else years_to_maturity(maturity, today)
    step = 1 / freq

    n = int(np.ceil(round(years * freq, 9)))  # round() stops 10.0 * 2 = 19.999... adding a period
    n = max(n, 1)  # maturing today (years=0): one final coupon + principal paid now

    # Needs times to go back words so you can figure out when the next cupon payment is
    # Ex Semi-anual cupons 5 year maturity .2 years in
    # Backwords: 4.8 -> 4.2 -> ... -> 0.2=next cupon payment
    times = years - step * np.arange(n)[::-1]  # oldest first, last one = maturity
    flows = np.full(n, face * coupon / 100 / freq)
    flows[-1] += face  # principal repaid with the last coupon
    
    return pd.DataFrame({"years": times, "cash_flow": flows})


def present_value(cf, ytm, compounding=2):
    r"""Discounts the rows from `cash_flows` back to today and adds them up, giving the bond's (dirty) price.
    `ytm` is a decimal (0.05 = 5%). `compounding` is how often the yield compounds:
    - a number `m` (1 = annual, 2 = semiannual, 4 = quarterly, 12 = monthly): $PV = \sum CF_t \,/\, (1 + y/m)^{m t}$
    - `"continuous"`: $PV = \sum CF_t \, e^{-y t}$

    The same yield gives a lower price with continuous compounding, because it compounds more often. To get the
    same price, convert the rate: $r_{cont} = m \ln(1 + y/m)$.
    Compounding is separate from coupon frequency: `cash_flows(freq=...)` sets when coupons are paid, `compounding` sets how the yield is applied.
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
    """Latest common-date 5/7/10Y yields as decimals, indexed by tenor in years.

    Gets the last 10 FRED prints of DGS5, DGS7 and DGS10 (`TENORS`) and keeps the latest date where all three exist.
    Returns those yields as decimals, indexed by tenor in years (5, 7, 10). The date is in `.attrs["as_of"]`.
    - Raises `RuntimeError` if none of the 10 dates has all three.
    - Not cached: every call fetches fresh from FRED (3 requests).
    """
    data = pd.concat({t: get_latest(sid, n=10) for t, sid in TENORS.items()}, axis=1).dropna()
    if data.empty:
        raise RuntimeError("No date in the last 10 FRED prints has all of DGS5, DGS7, DGS10.")
    latest = data.iloc[-1] / 100  # FRED quotes percent
    latest.attrs["as_of"] = data.index[-1].date()
    return latest


def treasury_yield(years):
    """Pulls DGS5, DGS7 and DGS10 from FRED and linearly interpolates the Treasury yield at that maturity.
    - All three come from the **same date** (latest date where all three exist).
    - Outside 5-10 years it holds the end value flat and warns. Add DGS2/DGS3/DGS20 if we need a wider range.
    - Calls `treasury_curve()` every time, so each call makes 3 FRED requests.
    """
    curve = treasury_curve()
    lo, hi = curve.index.min(), curve.index.max()
    if not lo <= years <= hi:
        print(f"Warning: {years:.2f}y is outside {lo}-{hi}y; using flat extrapolation.")
    return float(np.interp(years, curve.index, curve.values))


def spread(bond_yield, years):
    """The bond's yield minus the matching Treasury yield (decimal; multiply by 10,000 for bp).
    `bond_yield` will come from Brian's `ytm(price, coupon, years)`.
    """
    return bond_yield - treasury_yield(years)
