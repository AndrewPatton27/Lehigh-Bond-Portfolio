from collections.abc import Iterator

import requests
import pandas as pd
from scipy.optimize import brentq


def _check(data: dict) -> dict:
    """Raise FRED's own error message instead of a confusing KeyError later."""
    if "error_message" in data:
        raise RuntimeError(f"FRED error {data.get('error_code')}: {data['error_message']}")
    return data


def get_recent(series_id: str, api_key: str, n: int = 0, change_name: bool = True) -> pd.Series:
    params: dict = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    if n != 0:
        params["limit"] = n
        params["sort_order"] = "desc"

    series_request = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params=params,
        timeout=30,  # without a timeout a dead connection hangs forever
    )
    data = _check(series_request.json())

    df: pd.DataFrame = pd.DataFrame(data["observations"])

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # sort_index: with n > 0 FRED sends newest first; return oldest first like fred_api.get_latest
    df = df.set_index("date").sort_index()

    # get the name associated with the series_id
    if change_name:
        name_request = requests.get(
            "https://api.stlouisfed.org/fred/series",
            params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
            timeout=30,
        )
        series_name: str = _check(name_request.json())["seriess"][0]["title"]
    else:
        series_name = series_id

    return df["value"].rename(series_name)


# Assumes one cash flow per year, at the end of the year
def bond_price(
    face_value,
    coupon_rate,
    years_to_maturity,
    discount_rate,
):
    def cash_flow_generator() -> Iterator[tuple[float | int, int]]:
        year = 0
        while year < years_to_maturity:
            year += 1
            yield face_value * coupon_rate, year
        yield face_value, year

    # first index is the cash flow, second index is the year
    return sum(cash_flow / (1 + discount_rate) ** year for cash_flow, year in cash_flow_generator())


def ytm(price: float, coupon: float, years: int) -> float:
    def price_difference(discount_rate: float) -> float:
        return bond_price(100, coupon, years, discount_rate) - price

    return brentq(price_difference, -0.9999, 100)


def modified_duration(coupon: float, years: int, yield_to_maturity: float) -> float:
    face_value = 100
    price = bond_price(face_value, coupon, years, yield_to_maturity)

    present_value_times_time = sum(
        year * face_value * coupon / (1 + yield_to_maturity) ** year
        for year in range(1, years + 1)
    )
    present_value_times_time += years * face_value / (1 + yield_to_maturity) ** years

    macaulay_duration = present_value_times_time / price
    return macaulay_duration / (1 + yield_to_maturity)


def dv01(coupon: float, years: int, yield_to_maturity: float, face: float) -> float:
    price = bond_price(face, coupon, years, yield_to_maturity)
    duration = modified_duration(coupon, years, yield_to_maturity)
    return price * duration * 0.0001