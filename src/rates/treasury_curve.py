"""Treasury curve from FRED and bond spreads over it."""

import warnings

import numpy as np
import pandas as pd

from fred.fred_api import get_latest


TENORS = {5: "DGS5", 7: "DGS7", 10: "DGS10"}


def treasury_curve() -> pd.Series:
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


def treasury_yield(years: float, curve: pd.Series | None = None) -> float:
    """Return the Treasury yield at `years`, linearly interpolated.

    Uses the 5/7/10-year yields from treasury_curve(), all from the same date.
    Outside 5-10 years it holds the end value flat and issues a `UserWarning`.
    Each call makes 3 FRED requests unless `curve` is given.

    Args:
        years: Maturity in years.
        curve: A curve from treasury_curve(), to reuse across many calls. Fetched
            from FRED when omitted.

    Returns:
        The interpolated yield as a decimal.
    """
    if curve is None:
        curve = treasury_curve()
    lo, hi = curve.index.min(), curve.index.max()
    if not lo <= years <= hi:
        warnings.warn(f"{years:.2f}y is outside {lo}-{hi}y; using flat extrapolation.", UserWarning, stacklevel=2)
    return float(np.interp(years, curve.index, curve.values))


def spread(bond_yield: float, years: float, curve: pd.Series | None = None) -> float:
    """Return the bond's yield minus the Treasury yield at the same maturity.

    Args:
        bond_yield: The bond's yield as a decimal.
        years: The bond's years to maturity.
        curve: A curve from treasury_curve(), to reuse across many bonds. Fetched
            from FRED when omitted.

    Returns:
        The spread as a decimal; multiply by 10,000 for basis points.
    """
    return bond_yield - treasury_yield(years, curve)
