"""A single bond and its value and risk."""

import pandas as pd

from . import risk, valuation
from .tenor import DateLike, years_to_maturity

class Bond:
    """A bond position.

    Attributes:
        coupon: Annual coupon rate as a decimal (0.05 means 5%).
        maturity: Years left as a number, or a maturity date ("YYYY-MM-DD", date,
            datetime or Timestamp).
        face: Face value of the position, defaults to 100.
        freq: Coupons per year, defaults to 2. The yield compounds `freq` times a year.
        issuer, cusip, rating: Optional labels from the bond table.
    """

    def __init__(
        self,
        coupon: float,
        maturity: float | DateLike,
        face: float = 100.0,
        freq: int = 2,
        issuer: str | None = None,
        cusip: str | None = None,
        rating: str | None = None,
    ) -> None:
        """Create a bond position.

        Args:
            coupon: Annual coupon rate as a decimal (0.05 means 5%).
            maturity: Years left as a number, or a maturity date.
            face: Face value of the position.
            freq: Coupons per year. The yield compounds `freq` times a year.
            issuer: Issuer name from the bond table.
            cusip: CUSIP from the bond table.
            rating: Credit rating from the bond table.
        """
        self.coupon = coupon
        self.maturity = maturity
        self.face = face
        self.freq = freq
        self.issuer = issuer
        self.cusip = cusip
        self.rating = rating

    def years_to_maturity(self, today: DateLike | None = None) -> float:
        """Return the years from `today` to maturity.

        Args:
            today: Valuation date. Defaults to the current date. Ignored when
                `maturity` is a number of years.

        Returns:
            Years left, as a float.
        """
        if isinstance(self.maturity, valuation.NUMBER_TYPES):
            return float(self.maturity)
        return years_to_maturity(self.maturity, today)

    def cash_flows(self, today: DateLike | None = None) -> pd.DataFrame:
        """Return the remaining payments, soonest first.

        Args:
            today: Valuation date, used only when `maturity` is a date.

        Returns:
            A DataFrame with columns `years` and `cash_flow`, in the units of `face`.
        """
        return valuation.cash_flows(self.coupon, self.maturity, self.face, today, self.freq)

    def value(self, discount_rate: float, today: DateLike | None = None) -> float:
        """Return the dirty price of the position.

        The dirty (full) price is the present value of all remaining payments. It
        includes accrued interest, so it differs from a quoted clean price.

        Args:
            discount_rate: Yield as a decimal, compounding `freq` times a year.
            today: Valuation date, used only when `maturity` is a date.

        Returns:
            The present value of the remaining payments, in the units of `face`.
        """
        cf = self.cash_flows(today)
        return valuation.present_value(cf, discount_rate, compounding=self.freq)

    def ytm(self, price: float, today: DateLike | None = None) -> float:
        """Return the yield that prices the position at `price`.

        Args:
            price: Dirty price of the position, in the units of `face`.
            today: Valuation date, used only when `maturity` is a date.

        Returns:
            The yield as a decimal.
        """
        return valuation.ytm(price, self.coupon, self.years_to_maturity(today), self.face, self.freq)

    def modified_duration(self, discount_rate: float, today: DateLike | None = None) -> float:
        """Return the modified duration.

        Args:
            discount_rate: Yield as a decimal, compounding `freq` times a year.
            today: Valuation date, used only when `maturity` is a date.

        Returns:
            Modified duration in years.
        """
        return risk.modified_duration(self.coupon, self.years_to_maturity(today), discount_rate, self.freq)

    def dv01(self, discount_rate: float, today: DateLike | None = None, epsilon: float = 1e-4) -> float:
        """Return the price change of the position for a 1bp move in yield.

        Args:
            discount_rate: Yield as a decimal, compounding `freq` times a year.
            today: Valuation date, used only when `maturity` is a date.
            epsilon: Size of the yield bump used to reprice. Must be positive.

        Returns:
            DV01 in the units of `face`.

        Raises:
            ValueError: If `epsilon` is not positive.
        """
        return risk.dv01(
            self.face, self.coupon, self.years_to_maturity(today), discount_rate, self.freq, epsilon
        )


def bond_from_row(row: pd.Series, face: float = 100.0, freq: int = 2) -> Bond:
    """Build a bond from a row of load_bonds().

    Args:
        row: A row with `Coupon` (decimal) and `Maturity Date`, and optionally
            `Issuer`, `CUSIP` and `Rating`.
        face: Face value of the position.
        freq: Coupons per year.

    Returns:
        The bond.
    """
    return Bond(
        coupon=float(row["Coupon"]),
        maturity=row["Maturity Date"],
        face=face,
        freq=freq,
        issuer=row.get("Issuer"),
        cusip=row.get("CUSIP"),
        rating=row.get("Rating"),
    )
