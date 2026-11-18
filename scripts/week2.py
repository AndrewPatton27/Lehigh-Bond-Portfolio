import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "bondhedge"))
from bond_functions import dv01, bond_price


def main():
    print(dv01(0.05, 5, 0.04, 100))
    print(bond_price(100, 0.05, 5, 0.04))
    print(bond_price(100, 0.05, 5, 0.06))


if __name__ == '__main__':
    main()
