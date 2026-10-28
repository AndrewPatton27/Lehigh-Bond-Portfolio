import os
import pandas as pd
from dotenv import load_dotenv
from bond_functions import get_recent

load_dotenv()
api_key = os.environ["FRED_API_KEY"]

def main():
    series_ids = "BAMLC0A1CAAA", "BAMLC0A2CAA", "BAMLC0A3CA", "BAMLC0A4CBBB", "BAMLC0A0CM"

    curves = pd.concat([get_recent(i, api_key) for i in series_ids], axis=1)
    curves = curves.dropna()

    print(type(curves))
    print(curves)

if __name__ == '__main__':
    main()