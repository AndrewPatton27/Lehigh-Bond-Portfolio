from bonds.valuation import cash_flows
from bonds.valuation import present_value
from bonds.valuation import ytm


def main():
    cf = cash_flows(0.05, 3, 1000, freq=1)
    print(cf)
    price = present_value(cf, 0.04, 1)
    print(price)
    y = ytm(price, 0.05, 3, 1000, freq=1)
    print(y)


if __name__ == '__main__':
    main()