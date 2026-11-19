import pandas as pd
import math

class BondAlternate:
    def __init__(self, face_value: float | int, coupon_rate: float | int, years: int, annual_payments: int = 2) -> None:
        if isinstance(face_value, bool) or not isinstance(face_value, (int, float)):
            raise TypeError("face_value must be an int or float")
        if not math.isfinite(face_value) or face_value < 0:
            raise ValueError("face_value must be a finite, non-negative number")

        if isinstance(coupon_rate, bool) or not isinstance(coupon_rate, (int, float)):
            raise TypeError("coupon_rate must be an int or float")
        if not math.isfinite(coupon_rate) or not 0 <= coupon_rate <= 1:
            raise ValueError("coupon_rate must be between 0 and 1")

        if isinstance(years, bool) or not isinstance(years, int):
            raise TypeError("years must be an int")
        if years <= 0:
            raise ValueError("years must be positive")

        if isinstance(annual_payments, bool) or not isinstance(annual_payments, int):
            raise TypeError("annual_payments must be an int")
        if annual_payments <= 0:
            raise ValueError("annual_payments must be positive")

        self.face_value = face_value
        self.coupon_rate = coupon_rate
        self.years = years
        self.annual_payments = annual_payments

    def cash_flows(self) -> pd.DataFrame:
        year_list = []
        cash_flow_list = []
        for payment_number in range(1, self.years * self.annual_payments + 1):
            year_list.append(payment_number / self.annual_payments)
            cash_flow_list.append(self.face_value * self.coupon_rate / self.annual_payments)
        cash_flow_list[-1] += self.face_value
        return pd.DataFrame({"year": year_list, "cash flow": cash_flow_list})