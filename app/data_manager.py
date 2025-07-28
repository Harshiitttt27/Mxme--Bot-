import requests
import pandas as pd

def load_data(symbols, start, end, api_key):
    data = {}
    for symbol in symbols:
        url = f"https://api.polygon.io/v2/aggs/ticker/X:{symbol}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        response = requests.get(url)
        res = response.json()
        df = pd.DataFrame(res['results'])
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.rename(columns={"c": "close"}, inplace=True)
        data[symbol] = df
    return data
