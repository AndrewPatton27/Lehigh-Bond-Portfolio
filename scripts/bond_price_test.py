from bonds.risk import dv01
from bonds.valuation import bond_price


def main() -> None:
    # Print the DV01 and prices of a 5 year 5% bond at 4% and 6%.
    print(dv01(100, 0.05, 5, 0.04))
    print(bond_price(100, 0.05, 5, 0.04))
    print(bond_price(100, 0.05, 5, 0.06))


if __name__ == '__main__':
    main()
