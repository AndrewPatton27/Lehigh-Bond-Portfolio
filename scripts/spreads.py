from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
from fred.fred_api import get_series, get_series_info

def main() -> None:
    """Plot US corporate option-adjusted spreads by rating and save the chart."""
    series_ids = "BAMLC0A1CAAA", "BAMLC0A2CAA", "BAMLC0A3CA", "BAMLC0A4CBBB", "BAMLC0A0CM"

    # name each column after the series title (what get_recent did) for the plot legend
    curves = pd.concat([get_series(i).rename(get_series_info(i)["title"]) for i in series_ids], axis=1)
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
    out_dir = Path(__file__).resolve().parents[1] / "outputs" / Path(__file__).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / "spreads.png")
    plt.show()

if __name__ == '__main__':
    main()
