"""Modified duration and DV01."""

import pandas as pd

from .valuation import cash_flows, present_value


def _modified_duration(cf: pd.DataFrame, yield_to_maturity: float, freq: int) -> float:
    """Modified duration of the cash flows `cf`, discounted at `yield_to_maturity`.

    Raises:
        ValueError: If the yield is at or below `-freq` (1 + yield / freq would
            be 0 or less), or the cash flows sum to 0 (duration divides by it).
    """
    if yield_to_maturity <= -freq:
        raise ValueError(f"yield must be above -{freq} for {freq}x compounding, got {yield_to_maturity!r}")
    t = cf["years"].to_numpy()
    flows = cf["cash_flow"].to_numpy()
    discounted = flows * (1 + yield_to_maturity / freq) ** (-freq * t)

    total = discounted.sum()
    if total == 0:
        raise ValueError("modified duration is undefined: the cash flows sum to 0")
    macaulay_duration = (t * discounted).sum() / total
    return macaulay_duration / (1 + yield_to_maturity / freq)


def modified_duration(coupon: float, years: float, yield_to_maturity: float, freq: int = 2) -> float:
    """Return the modified duration of a bond.

    Args:
        coupon: Annual coupon as a decimal (0.05 means 5%).
        years: Years left, fractional allowed.
        yield_to_maturity: Yield as a decimal.
        freq: Coupons per year, and yield compounding per year.

    Returns:
        Modified duration in years.
    """
    cf = cash_flows(coupon, years, face=100, freq=freq)
    return _modified_duration(cf, yield_to_maturity, freq)


def dv01_linear(face: float, coupon: float, years: float, yield_to_maturity: float, freq: int = 2) -> float:
    """Return DV01 from duration: price x modified duration x 1bp.

    Args:
        face: Face value of the position.
        coupon: Annual coupon as a decimal (0.05 means 5%).
        years: Years left, fractional allowed.
        yield_to_maturity: Yield as a decimal.
        freq: Coupons per year, and yield compounding per year.

    Returns:
        The approximate price change for a 1bp move, in the units of `face`.
    """
    if face == 0:  # no position, and duration would be 0 / 0
        return 0.0
    cf = cash_flows(coupon, years, face=face, freq=freq)
    price = present_value(cf, yield_to_maturity, freq)
    duration = _modified_duration(cf, yield_to_maturity, freq)
    return price * duration * 0.0001

def dv01(
    face: float,
    coupon: float,
    years: float,
    yield_to_maturity: float,
    freq: int = 2,
    epsilon: float = 1e-4,
) -> float:
    """Return DV01 from repricing: the price change for a 1bp move in yield.

    Reprices at `yield_to_maturity` plus and minus `epsilon` (central difference)
    and scales to 1bp.

    Args:
        face: Face value of the position.
        coupon: Annual coupon as a decimal (0.05 means 5%).
        years: Years left, fractional allowed.
        yield_to_maturity: Yield as a decimal.
        freq: Coupons per year, and yield compounding per year.
        epsilon: Size of the yield bump used to reprice. Must be positive.

    Returns:
        The price change for a 1bp move, in the units of `face`.

    Raises:
        ValueError: If `epsilon` is not positive (the result divides by it).
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be positive, got {epsilon!r}")
    BP = 0.0001
    cf = cash_flows(coupon, years, face=face, freq=freq)  # built once for both bumps
    price_up = present_value(cf, yield_to_maturity + epsilon, freq)
    price_down = present_value(cf, yield_to_maturity - epsilon, freq)

    # Average dv01 for an increase and a decrease of one basis point (BP)
    # dv01_up = (price - price_up) * BP / epsilon
    # dv01_down = (price_down - price) * BP / epsilon
    # return (dv01_up + dv01_down) / 2

    # The P(y) (price) cancels out
    # −[P(y+e) − P(y−e)] / (2e) × 0.0001
    return -(price_up - price_down) / (2*epsilon) * BP
