import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from matplotlib import pyplot as plt
from bond_functions import get_recent

load_dotenv()
api_key = os.environ["FRED_API_KEY"]

def main():
    maturities = {
        "DGS1MO": 1/12, "DGS3MO": 1/4, "DGS6MO": 1/2,
        "DGS1": 1, "DGS2": 2, "DGS3": 3, "DGS5": 5,
        "DGS7": 7, "DGS10": 10, "DGS20": 20, "DGS30": 30,
    }
    durations = list(maturities.values())

    curves = pd.concat([get_recent(i, api_key, 10, False) for i in maturities], axis=1)
    curves = curves.dropna()

    print(curves)

    latest_date = curves.index.max()
    latest: pd.Series = curves.loc[latest_date]

    plt.plot(durations, latest.values, marker="o", markersize=3)
    plt.xscale("log")
    plt.xticks(durations, ("1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"))
    plt.xlabel("Maturity")
    plt.ylabel("Yield (%)")
    plt.title(f"US Treasury Yield Curve, {latest_date:%Y-%m-%d}")
    plt.grid(alpha=0.3)
    plt.savefig(Path(__file__).with_name("yield-curve.png"))
    plt.show()


if __name__ == "__main__":
    main()
