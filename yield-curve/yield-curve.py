import pandas as pd
import requests
from pathlib import Path
from matplotlib import pyplot as plt

key = Path(".env").read_text().strip()

def main():
    maturities = {
        "DGS1MO": 1/12, "DGS3MO": 1/4, "DGS6MO": 1/2,
        "DGS1": 1, "DGS2": 2, "DGS3": 3, "DGS5": 5,
        "DGS7": 7, "DGS10": 10, "DGS20": 20, "DGS30": 30,
    }
    durations = list(maturities.values())

    curves = pd.concat([get_recent(i) for i in maturities], axis=1)
    curves = curves.dropna()

    print(curves)

    latest_date = curves.index[0]
    latest: pd.Series = curves.iloc[0]

    plt.plot(durations, latest.values, marker="o", markersize=3)
    plt.xscale("log")
    plt.xticks(durations, ("1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"))
    plt.xlabel("Maturity")
    plt.ylabel("Yield (%)")
    plt.title(f"US Treasury Yield Curve, {latest_date:%Y-%m-%d}")
    plt.grid(alpha=0.3)
    plt.savefig("yield-curve/yield-curve.png")
    plt.show()


def get_recent(series_id, n=10) -> pd.Series:
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

    df: pd.DataFrame = pd.DataFrame(r.json()["observations"])

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.set_index("date")

    return df["value"].rename(series_id)


if __name__ == "__main__":
    main()