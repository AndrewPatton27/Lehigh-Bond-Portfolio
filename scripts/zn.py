import yfinance as yf

def main():
    ticker = "ZN=F"
    data = yf.download(ticker)
    print(data["Close"][ticker])

if __name__ == '__main__':
    main()