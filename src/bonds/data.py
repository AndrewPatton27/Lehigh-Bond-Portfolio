"""Load the bond table CSV."""

from pathlib import Path

import pandas as pd


def load_bonds(csv: str | Path) -> pd.DataFrame:
    """Read the bond table.

    Expected columns: Issuer, CUSIP, Coupon (%), Maturity Date, Price, Rating.

    Args:
        csv: Path to the CSV file.

    Returns:
        A DataFrame where `Coupon (%)` is replaced by `Coupon`, a decimal
        (4.375 becomes 0.04375), and `Maturity Date` is parsed to
        `datetime.date`, so the other functions can use the rows directly.
    """
    bonds = pd.read_csv(csv)
    bonds.columns = bonds.columns.str.strip()
    # percent in the file, decimal everywhere else
    bonds["Coupon"] = bonds.pop("Coupon (%)") / 100
    # normalize the date format
    bonds["Maturity Date"] = pd.to_datetime(bonds["Maturity Date"]).dt.date
    return bonds
