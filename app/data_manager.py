# FILE: app/data_manager.py

import requests
import pandas as pd
from app.utils import safe_get  # 👈 import safe_get here

def load_data(symbols, start, end, api_key):
    data = {}
    for symbol in symbols:
        symbol = symbol.strip().upper()
        url = f"https://api.polygon.io/v2/aggs/ticker/X:{symbol}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        
        response = safe_get(url)  # ✅ Use the retry-safe function here

        if not response:
            print(f"[FAIL] Could not fetch data for {symbol}")
            continue

        try:
            res = response.json()
            if 'results' not in res or not res['results']:
                print(f"[NO DATA] {symbol}: No results returned")
                continue

            df = pd.DataFrame(res['results'])
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df.rename(columns={"c": "close"}, inplace=True)

            data[symbol] = df

        except Exception as e:
            print(f"[ERROR] Failed to parse data for {symbol}: {e}")
            continue

    return data
