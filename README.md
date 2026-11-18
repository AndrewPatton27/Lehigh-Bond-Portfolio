# Lehigh-Bond-Portfolio
Lehigh Quant Club bond portfolio project 2026

Hedging the interest-rate risk of a 2x-levered investment-grade corporate bond
portfolio with CME 5-year (ZF) and 10-year (ZN) Treasury futures, and measuring the
fund's net yield after costs.

## Setup

Requires Python 3.10 or newer.

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .                # installs the packages in src/ plus requirements.txt
```

FRED API key (free: https://fredaccount.stlouisfed.org/apikeys): copy `.env.example`
to `.env` in the repo root and fill in `FRED_API_KEY`. `.env` is git-ignored; never
commit a real key.

Run a script from the repo root, for example:

```
python scripts/spreads.py
```

Scripts save their output to `outputs/<script name>/`.

## File structure

```
src/                     installable packages (pip install -e .)
  bonds/
    bond.py              Bond class (one position) and bond_from_row()
    portfolio.py         Portfolio: a list of Bond; add_table(), get_value(), get_dv01()
    valuation.py         cash_flows(), present_value(), bond_value(), bond_value_from_series(), ytm()
    risk.py              modified_duration(), dv01() (reprice), dv01_linear() (duration approx.)
    tenor.py             years_between(), years_to_maturity()
    data.py              load_bonds(): read the bond table CSV
  fred/
    fred_api.py          FRED helper: get_series(), get_latest(), get_dataset(), clean_dataset(), ...
  rates/
    treasury_curve.py    treasury_curve(), treasury_yield(), spread()
scripts/                 runnable analysis scripts
  spreads.py             corporate OAS by rating
  yield-curve.py         latest Treasury yield curve
  t_rates.py             5Y/10Y Treasury yields and SOFR (percent-format, "# %%" cells)
  bonds_live_demo.py     price vs yield demo (percent-format)
  week2.py               Week 2 price and DV01 check
outputs/<script name>/   charts and CSVs each script writes
pyproject.toml           package config (setuptools, src layout)
requirements.txt         pinned runtime dependencies
.env.example             template for .env
```

Import from the packages directly, for example
`from bonds.valuation import bond_value` or `from fred.fred_api import get_series`.
Do not add `sys.path` hacks or `from src. ...` imports.

## Conventions

Units
- Coupons, yields and spreads are **decimals**: 0.05 means 5%. `load_bonds()` turns
  the table's `Coupon (%)` column into a decimal `Coupon` column. A coupon above 1
  raises `ValueError`.
- FRED quotes percent; the code divides by 100 where it reads Treasury yields.
- Time is in **years**, fractional allowed (4.5 is fine). Maturity can also be a date
  (`"YYYY-MM-DD"`, `date`, `datetime`, `Timestamp`).

Pricing
- `face` is the first argument of the pricing and DV01 functions and defaults to 100.
  It will become the real position size.
- Default coupon frequency and yield compounding are **semiannual** (`freq=2`,
  `compounding=2`), as US Treasuries pay. `compounding` must be a positive number
  (1 annual, 2 semiannual, 4 quarterly, 12 monthly); continuous compounding is not
  supported.
- Coupon dates count back from maturity in 1/freq-year steps, so the first period
  can be short.
- Currently uses **dirty** pricing in `bond_value()` and `present_value()`(accrued interest is not removed)
- `years_between()` is close to actual/actual. The day count is not final.

Errors
- Bad input raises `ValueError`; FRED failures raise `FredError`.

Data and secrets
- API keys live only in `.env`.
- `*.csv` is git-ignored