import os
import pandas as pd
from dotenv import load_dotenv
from requests import get

load_dotenv()
api_key = os.environ["FRED_API_KEY"]

def main():
    series_id = "BAMLC0A0CM"

    r = get(
        "https://api.stlouisfed.org/fred/series/observations",
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
        }
    )

    r.raise_for_status()

    df: pd.DataFrame = pd.DataFrame(r.json()["observations"])

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.set_index("date")
    series: pd.Series = df["value"].rename("Investment grade")

    print(series)

if __name__ == '__main__':
    main()