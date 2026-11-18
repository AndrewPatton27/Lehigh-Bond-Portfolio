"""
FRED API helper for the Lehigh Bond Portfolio project

Setup:
    Get a free API key: https://fredaccount.stlouisfed.org/apikeys
    Put it in the repo root .env as:  FRED_API_KEY=your_key_here

Usage:
    from fred_api import get_series, get_dataset, report_missing, clean_dataset

    ten_year = get_series("DGS10", start="2020-01-01")
    rates = get_dataset({"UST_5Y": "DGS5", "UST_10Y": "DGS10", "SOFR": "SOFR"})
    report_missing(rates)
    rates = clean_dataset(rates)  # common date range, short gaps filled, no NaNs
"""

import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()  # finds the repo root .env by searching up from this file's folder

BASE_URL = "https://api.stlouisfed.org/fred"
TIMEOUT_SECONDS = 30


class FredError(RuntimeError):
    """Raised when FRED cannot be reached or returns an error or unusable data."""


def get_api_key() -> str:
    """Return the FRED API key from the environment (loaded from .env)."""
    key = os.environ.get("FRED_API_KEY", "").strip()  # "" default: unset key hits the FredError below
    if not key:
        raise FredError(
            "FRED_API_KEY is not set. Add it to the repo root .env "
            "(see .env.example); never hard code or commit your real key"
        )
    return key


def fred_get(endpoint: str, **params) -> dict:
    """Call a FRED endpoint and return the parsed JSON."""
    key = get_api_key()
    params = {**params, "api_key": key, "file_type": "json"}
    try:
        resp = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # `from None`: requests error messages embed the URL, which contains the key
        raise FredError(f"Could not reach FRED ({type(exc).__name__}).") from None

    try:
        data = resp.json()
    except ValueError:
        # Show what actually came back (never print the API key)
        raise FredError(
            f"FRED returned invalid responce.\n  status: {resp.status_code}\n"
            f"  content-type: {resp.headers.get('Content-Type')}\n"
            f"  body (first 300 chars): {resp.text[:300]!r}\n"
            f"  possible invalid key - FRED KEY len: {len(key)} (FRED keys are 32 chars)"
        ) from None

    if "error_message" in data:
        raise FredError(f"FRED error {data.get('error_code')}: {data['error_message']}")
    return data


def _to_series(observations: list[dict], series_id: str) -> pd.Series:
    """Turn FRED observations into a date-indexed float Series."""
    if not observations:
        raise FredError(f"FRED returned no observations for {series_id}.")
    df = pd.DataFrame(observations)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # "." = missing
    return df.set_index("date")["value"].rename(series_id)


def get_series(series_id: str, start: str | None = None, end: str | None = None) -> pd.Series:
    """Fetch a series as a date-indexed float Series (oldest first).

    start/end are YYYY-MM-DD strings; omit for FRED's defaults (full history).
    """
    params = {"series_id": series_id}
    if start:
        params["observation_start"] = start
    if end:
        params["observation_end"] = end
    obs = fred_get("series/observations", **params)["observations"]
    return _to_series(obs, series_id)


def get_latest(series_id: str, n: int = 10) -> pd.Series:
    """Fetch the most recent n observations of a series (oldest first)."""
    obs = fred_get(
        "series/observations", series_id=series_id, sort_order="desc", limit=n
    )["observations"]
    return _to_series(obs, series_id).sort_index()


def get_dataset(
    series: dict[str, str],
    start: str | None = None,
    end: str | None = None,
    ffill: bool = False,
) -> pd.DataFrame:
    """Fetch several series and align them on date.

    series maps column name -> FRED series ID, e.g. {"UST_10Y": "DGS10"}.
    Uses an outer join so no observation is silently dropped, then removes dates
    where every series is missing. Remaining gaps stay NaN unless ffill=True.
    """
    data = pd.concat(
        {name: get_series(sid, start, end) for name, sid in series.items()}, axis=1
    ).sort_index()
    data.index.name = "date"
    data = data.dropna(how="all")
    return data.ffill() if ffill else data


def report_missing(data: pd.DataFrame, max_listed: int = 15) -> None:
    """Print the date range and any missing observations per series."""
    if data.empty:  # min()/max() of an empty index is NaT, which can't be formatted
        print("0 rows")
        return
    print(f"{len(data)} rows, {data.index.min():%Y-%m-%d} to {data.index.max():%Y-%m-%d}")
    for col in data.columns:
        missing = data.index[data[col].isna()]
        print(f"  {col}: {len(missing)} missing observation(s)")
        if 0 < len(missing) <= max_listed:
            print("    dates:", ", ".join(f"{d:%Y-%m-%d}" for d in missing))

def fill_gaps(data: pd.DataFrame, limit: int | None = 3) -> pd.DataFrame:
    """Forward-fill short gaps (holidays, one-off missing prints).

    limit caps how many consecutive missing days get filled, so a long outage
    stays NaN instead of being covered by a stale value. None = no cap, 0 = no fill.
    """
    if limit == 0:  # pandas rejects limit=0
        return data
    return data.ffill(limit=limit)


def drop_missing(data: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Drop dates where any of the given columns (default: all) is missing."""
    return data.dropna(how="any", subset=columns)


def clean_dataset(data: pd.DataFrame, fill_limit: int | None = 0) -> pd.DataFrame:
    """Fill limit is how big of a gap in the data to fill before just dropping it"""
    return drop_missing(fill_gaps(data, fill_limit))


def get_series_info(series_id: str) -> dict:
    """Return a series' metadata (title, units, frequency, date range, last update)."""
    info = fred_get("series", series_id=series_id)["seriess"]
    if not info:
        raise FredError(f"FRED has no series with ID {series_id}.")
    return info[0]


def search_series(text: str, limit: int = 5) -> pd.DataFrame:
    """Search for series by keyword."""
    res = fred_get("series/search", search_text=text, limit=limit)["seriess"]
    columns = ["id", "title", "frequency_short", "units_short"]
    return pd.DataFrame(res, columns=columns)


if __name__ == "__main__":
    # Example
    info = get_series_info("DGS10")
    print(f"{info['id']}: {info['title']} ({info['units_short']}, {info['frequency_short']})")
    print(get_latest("DGS10", n=5))
