import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from matplotlib import pyplot as plt
from bond_functions import get_recent

load_dotenv()
api_key = os.environ["FRED_API_KEY"]

def main():
    series_ids = "BAMLC0A1CAAA", "BAMLC0A2CAA", "BAMLC0A3CA", "BAMLC0A4CBBB", "BAMLC0A0CM"

    curves = pd.concat([get_recent(i, api_key) for i in series_ids], axis=1)
    curves = curves.dropna()

    print(curves)

    fig, ax = plt.subplots(layout="constrained")
    ax.set_title("US Corporate OAS by Rating")
    ax.set_xlabel("Date")
    ax.set_ylabel("Option-adjusted spread (%)")
    ax.plot(curves, label=curves.columns)
    ax.tick_params("x", rotation=45)
    ax.grid(alpha=0.4)
    fig.legend(loc="outside lower center")
    plt.savefig(Path(__file__).with_name("spreads.png"))
    plt.show()

if __name__ == '__main__':
    main()