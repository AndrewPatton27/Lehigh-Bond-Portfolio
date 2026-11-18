"""A portfolio of bonds."""

import pandas as pd

from .bond import Bond, bond_from_row
from .tenor import DateLike


class Portfolio:
    """A list of bonds, valued and risked together."""

    def __init__(self, bonds: list[Bond] | None = None) -> None:
        """Create a portfolio.

        Args:
            bonds: The bonds to hold. Defaults to none.
        """
        self.bonds: list[Bond] = list(bonds or [])

    def add_table(self, table: pd.DataFrame, face: float = 100.0, freq: int = 2) -> None:
        """Add one Bond per row of load_bonds() to this portfolio.

        Args:
            table: The DataFrame from load_bonds().
            face: Face value given to every bond.
            freq: Coupons per year given to every bond.
        """
        self.bonds.extend(bond_from_row(row, face, freq) for _, row in table.iterrows())

    def get_value(self, discount_rate: float, today: DateLike | None = None) -> float:
        """Return the portfolio value: the sum of each bond's value.

        Args:
            discount_rate: Yield as a decimal, applied to every bond.
            today: Valuation date, used by bonds whose maturity is a date.

        Returns:
            The total value, in the units of `face`.
        """
        return sum(bond.value(discount_rate, today) for bond in self.bonds)

    def get_dv01(self, discount_rate: float, today: DateLike | None = None, epsilon: float = 1e-4) -> float:
        """Return the portfolio DV01: the sum of each bond's DV01.

        Args:
            discount_rate: Yield as a decimal, applied to every bond.
            today: Valuation date, used by bonds whose maturity is a date.
            epsilon: Size of the yield bump used to reprice. Must be positive.

        Returns:
            The total price change for a 1bp move, in the units of `face`.
        """
        return sum(bond.dv01(discount_rate, today, epsilon) for bond in self.bonds)
