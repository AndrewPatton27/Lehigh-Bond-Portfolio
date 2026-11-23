import numpy as np
import pandas as pd

def _be_type(value, name: str, types: tuple[type, ...]) -> None:
    if isinstance(value, bool) or not isinstance(value, types):
        type_names = types[0].__name__ if len(types) == 1 else " or ".join(t.__name__ for t in types)
        raise TypeError(f"{name} must be a {type_names}")

def _be_positive(value: int | float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")

class BondAlternate:
    def __init__(self, face_value: float | int, coupon_rate: float | int, years: int, annual_payments: int = 2) -> None:
        _be_type(face_value, "face_value", (int, float))
        _be_positive(face_value, "face_value")

        _be_type(coupon_rate, "coupon_rate", (float,))
        if not 0 < coupon_rate < 1:
            raise ValueError("coupon_rate must be greater than 0 and less than 1")

        _be_type(years, "years", (int,))
        _be_positive(years, "years")

        _be_type(annual_payments, "annual_payments", (int,))
        _be_positive(annual_payments, "annual_payments")

        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.years = years
        self.annual_payments = annual_payments

    def cash_flows(self) -> pd.DataFrame:
        n = self.years * self.annual_payments
        df = pd.DataFrame({
            "Year": (np.arange(1, n + 1) / self.annual_payments),
            "Cash flow": self.face_value * self.coupon_rate / self.annual_payments
        }).set_index("Year")
        df.iloc[-1, -1] += self.face_value  # type: ignore[unsupported-operator]
        return df

    def price(self, discount_rate: float | int) -> float | int:
        _be_type(discount_rate, "discount_rate", (float,))

        cfs = self.cash_flows()
        years = cfs.index.to_numpy()
        flows = cfs["Cash flow"].to_numpy()

        factors = (1 + discount_rate / self.annual_payments) ** (-years * self.annual_payments)
        return (flows * factors).sum()

def main():
    bond = BondAlternate(100, 0.05, 3)
    print(bond.cash_flows())
    print(bond.price(0.04))
    print(bond.price(0.06))

if __name__ == "__main__":
    main()