import sys
from pathlib import Path
from src.bond_functions import bond_price

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "bondhedge"))


def main():
    print(bond_price(100, 0.05, 5, 0.04))
    print(bond_price(100, 0.05, 5, 0.06))


if __name__ == '__main__':
    main()
