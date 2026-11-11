from bond_functions import dv01, bond_price


def main():
    print(dv01(100_000_000, 6))
    print(bond_price(100, 0.05, 5, 0.04))
    print(bond_price(100, 0.05, 5, 0.06))


if __name__ == '__main__':
    main()
