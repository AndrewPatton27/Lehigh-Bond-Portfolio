"""Bond cash flows, present value, price and yield to maturity.

Conventions:
    coupon: Annual rate as a decimal (0.05 means 5%).
    yields and spreads: Decimals (0.0488 means 4.88%).
    time: Years.
    face: Defaults to 100.
    freq: Coupons per year, defaults to 2 (US Treasuries pay semiannually).
"""


import numpy as np
import pandas as pd
from scipy.optimize import brentq

from .tenor import DateLike, years_to_maturity

# int and float, plus their numpy versions: a plain number, not a date or a string
NUMBER_TYPES = (int, float, np.integer, np.floating)

def cash_flows(
    coupon: float,
    maturity: float | DateLike,
    face: float | None = 100.0,
    today: DateLike | None = None,
    freq: int = 2,
) -> pd.DataFrame:
    """Return a bond's remaining payments, soonest first.

    Coupon dates are counted back from maturity in 1/freq-year steps, so the
    first coupon can fall less than 1/freq years from today. The last payment
    includes the principal.

    Args:
        coupon: Annual coupon rate as a decimal (0.05 means 5%).
        maturity: Years left as a number, or a maturity date ("YYYY-MM-DD",
            date, datetime or Timestamp) converted with years_to_maturity.
        face: Face value; amounts are per `face`. None is treated as 0.
        today: Reference date, used only when `maturity` is a date.
        freq: Coupons per year (1 annual, 2 semiannual, 4 quarterly, 12 monthly).

    Returns:
        A DataFrame with columns `years` (time to each payment) and
        `cash_flow` (amount paid, in the units of `face`).

    Raises:
        ValueError: If `maturity` is a date in the past or a negative number
            of years, if `coupon` is negative or above 1, or if `freq` is not
            positive.

    Note:
        The first payment is a full coupon with no accrued interest removed, so
        present_value() of these flows is the dirty price between coupon dates.

    Example:
        cash_flows(0.05, 2) pays 2.5 at 0.5, 1.0 and 1.5 years and 102.5 at 2.0.
        cash_flows(0.05, 2, freq=1) pays 5 at 1.0 years and 105 at 2.0.
    """
    if face is None:
        face = 0
    if isinstance(freq, bool) or not isinstance(freq, NUMBER_TYPES) or freq <= 0:
        raise ValueError(f"freq must be a positive number, got {freq!r}")  # freq divides below
    if coupon < 0 or coupon > 1:
        raise ValueError(f"coupon is a decimal between 0 and 1 (0.05 means 5%), got {coupon!r}")

    # NUMBER_TYPES includes numpy numbers, so np.int64 counts as years, not as a date.
    years = maturity if isinstance(maturity, NUMBER_TYPES) else years_to_maturity(maturity, today)
    if years < 0:
        raise ValueError(f"maturity must be 0 or more years, got {years!r}")
    step = 1 / freq

    # Round first so float noise (10.0 * 2 = 19.999...) does not add a payment.
    n = int(np.ceil(round(years * freq, 9)))
    n = max(n, 1)  # years=0 still pays the last coupon and principal

    # Count back from maturity, e.g. 4.8 years: 4.8, 4.3, ..., 0.3 (next coupon).
    times = years - step * np.arange(n)[::-1]
    flows = np.full(n, face * coupon / freq)
    flows[-1] += face  # principal is repaid with the last coupon

    return pd.DataFrame({"years": times, "cash_flow": flows})

def bond_value(
    face_value: float, coupon_rate: float, years_to_maturity: float, discount_rate: float, freq: int = 2
) -> float:
    """Value a bond from numbers.

    To value a row of the bond table, use bond_value_from_series().

    Args:
        face_value: Face value of the position.
        coupon_rate: Annual coupon as a decimal (0.05 means 5%).
        years_to_maturity: Years left, fractional allowed.
        discount_rate: Yield as a decimal. Compounds `freq` times a year.
        freq: Coupons per year. Defaults to 2.

    Returns:
        The dirty price of the position, in the units of `face_value`.

    Raises:
        TypeError: If `face_value` is not a number.
        ValueError: If `coupon_rate` is above 1 (percent passed as a decimal).
    """
    if isinstance(face_value, bool) or not isinstance(face_value, NUMBER_TYPES):
        raise TypeError(f"face_value must be a number, got {type(face_value).__name__}")
    cf = cash_flows(coupon_rate, years_to_maturity, face=face_value, freq=freq)
    return present_value(cf, discount_rate, compounding=freq)

def bond_value_from_series(bond: pd.Series, discount_rate: float, today: DateLike | None = None, freq: int = 2) -> float:
    """Value one row of the bond table, per 100 face.

    Args:
        bond: A row from load_bonds() with `Coupon` (decimal) and `Maturity Date`.
        discount_rate: Yield as a decimal. Compounds `freq` times a year.
        today: Valuation date. Defaults to the current date.
        freq: Coupons per year. Defaults to 2.

    Returns:
        The dirty price of the bond, per 100 face.
    """
    cf = cash_flows(bond["Coupon"], bond["Maturity Date"], today=today, freq=freq)
    return present_value(cf, discount_rate, compounding=freq)

def present_value(cf: pd.DataFrame, ytm: float, compounding: int = 2) -> float:
    """Discount cash flows to today and sum them: the bond's dirty price.

    Args:
        cf: DataFrame from cash_flows() with `years` and `cash_flow` columns.
        ytm: Yield as a decimal (0.05 means 5%).
        compounding: Yield compounding per year (1 annual, 2 semiannual,
            4 quarterly, 12 monthly). This is separate from the coupon
            frequency set by cash_flows(freq=...).

    Returns:
        Present value as a float: sum(CF * (1 + y/m) ** (-m * t)).

    Raises:
        ValueError: If `compounding` is not a positive number, or if
            `ytm <= -compounding` (the discount factor is not defined).
    """
    t = cf["years"].to_numpy(dtype=float)
    flows = cf["cash_flow"].to_numpy(dtype=float)

    if not isinstance(compounding, NUMBER_TYPES) or compounding <= 0:
        raise ValueError(f"compounding must be a positive number, got {compounding!r}")
    if ytm <= -compounding:  # 1 + ytm / compounding would be 0 or less
        raise ValueError(f"yield must be above -{compounding} for {compounding}x compounding, got {ytm!r}")
    factors = (1 + ytm / compounding) ** (-compounding * t)

    return float((flows * factors).sum())


def ytm(price: float, coupon: float, years: float, face: float = 100, freq: int = 2) -> float:
    """Return the yield that prices the bond at `price`.

    Args:
        price: Dirty price of the position, in the units of `face`.
        coupon: Annual coupon as a decimal (0.05 means 5%).
        years: Years left, fractional allowed.
        face: Face value of the position.
        freq: Coupons per year, and yield compounding per year.

    Returns:
        The yield as a decimal.

    Raises:
        ValueError: If `price` is not positive, or no yield between -99.99% and
            10000% gives that price.
    """
    if price <= 0:
        raise ValueError(f"price must be positive, got {price!r}")

    cf = cash_flows(coupon, years, face=face, freq=freq)  # built once, reused by every iteration

    def price_difference(discount_rate: float) -> float:
        """Model price minus target price at `discount_rate`."""
        return present_value(cf, discount_rate, compounding=freq) - price

    try:
        return brentq(price_difference, -0.9999, 100)
    except ValueError:
        raise ValueError(f"no yield between -99.99% and 10000% gives price {price!r}") from None
