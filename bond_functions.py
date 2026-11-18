from collections.abc import Iterator
import requests
import pandas as pd


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
        params
    )

    df: pd.DataFrame = pd.DataFrame(series_request.json()["observations"])

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.set_index("date")

    # get the name associated with the series_id
    if change_name:
        name_request = requests.get(
            "https://api.stlouisfed.org/fred/series",
            {"series_id": series_id, "api_key": api_key, "file_type": "json"},
        )
        series_name: str = name_request.json()["seriess"][0]["title"]
    else:
        series_name = series_id

    return df["value"].rename(series_name)


def cash_flow_generator(years_to_maturity: int, face_value: int, coupon_rate: float | int) -> Iterator[tuple[float | int, int]]:
    year = 0
    while year < years_to_maturity:
        year += 1
        yield face_value * coupon_rate, year
    yield face_value, year


def discounted_cash_flow(cash_flow: float | int, year: int, discount_rate: float | int) -> float | int:
    return cash_flow / (1 + discount_rate) ** year


def bond_price(face_value: int, coupon_rate: float | int, years_to_maturity: int, discount_rate: float | int) -> float | int:
    return sum(
        discounted_cash_flow(cash_flow, year, discount_rate)
        for cash_flow, year in cash_flow_generator(
            years_to_maturity,
            face_value,
            coupon_rate,
        )
    )


def duration(coupon_rate: float | int, face_value, years: int, discount_rate: float | int) -> float | int:
    return sum(year * discounted_cash_flow(cash_flow, year, discount_rate) for cash_flow, year in
               cash_flow_generator(years, face_value, coupon_rate))


def modified_duration(face_value, coupon_rate: float | int, years: int, discount_rate: float | int) -> float | int:
    price = bond_price(face_value, coupon_rate, years, discount_rate)
    dur = duration(coupon_rate, face_value, years, discount_rate)
    return dur / price / (1 + discount_rate)


def dv01(price: float | int, dur) -> float | int:
    return price * dur * 0.0001