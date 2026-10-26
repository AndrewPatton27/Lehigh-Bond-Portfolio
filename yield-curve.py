import pandas as pd
import requests
from pathlib import Path

from matplotlib import pyplot as plt

key = Path("mykey.txt").read_text().strip()

def main():
    maturities = {
        "DGS1MO": 1/12, "DGS3MO": 1/4, "DGS6MO": 1/2,
        "DGS1": 1, "DGS2": 2, "DGS3": 3, "DGS5": 5,
        "DGS7": 7, "DGS10": 10, "DGS20": 20, "DGS30": 30,
    }

    curves = pd.concat([get_recent(s) for s in maturities], axis=1)
    curves = curves.dropna().sort_index()

    latest_date = curves.index[-1]
    latest = curves.iloc[-1]

    plt.figure(figsize=(9, 5))
    plt.plot([maturities[s] for s in latest.index], latest.values, marker="o")
    plt.xscale("log")
    plt.xticks(
        [1/12, 0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30],
        ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"],
    )
    plt.xlabel("Maturity")
    plt.ylabel("Yield (%)")
    plt.title(f"US Treasury Yield Curve, {latest_date:%Y-%m-%d}")
    plt.grid(alpha=0.3)
    plt.show()


def get_recent(series_id, n=10):
    r = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": n,
        },
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["observations"])
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.set_index("date")["value"].rename(series_id)


if __name__ == "__main__":
    main()