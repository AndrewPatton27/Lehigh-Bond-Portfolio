from src.bond_functions import bond_price


def main():
    print(f"{bond_price(100, 0.05, 5, 0.04):.2f}")
    print(f"{bond_price(100, 0.05, 5, 0.06):.2f}")


if __name__ == '__main__':
    main()
