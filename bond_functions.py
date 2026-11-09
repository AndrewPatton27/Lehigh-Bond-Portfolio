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


# dollar gain/loss when yields move one basis point
def dv01(market_value: float | int, duration):
    return market_value * duration * 0.0001  # 0.0001 is 1 basis point
