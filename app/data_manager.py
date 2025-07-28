import requests
import pandas as pd

def load_data(symbols, start, end, api_key):
    data = {}
    for symbol in symbols:
        symbol = symbol.strip().upper()
        url = f"https://api.polygon.io/v2/aggs/ticker/C:{symbol}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        response = requests.get(url)
        print(f"\nSymbol: {symbol}\nStatus Code: {response.status_code}\nResponse: {response.json()}")
        res = response.json()

        if 'results' not in res or not res['results']:
            print(f"Error fetching data for {symbol}: No data available")
            continue

        df = pd.DataFrame(res['results'])
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.rename(columns={"c": "close"}, inplace=True)
        data[symbol] = df

    return data

