import requests
import pandas as pd


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


# dollar gain/loss when yields move one basis point
def dv01(market_value: float | int, duration):
    return market_value * duration * 0.0001  # 0.0001 is 1 basis point
