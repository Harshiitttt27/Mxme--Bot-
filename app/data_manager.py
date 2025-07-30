# FILE: app/data_manager.py
# FILE: app/data_manager.py

import requests
import pandas as pd
from app.utils import safe_get  # 👈 import safe_get here


# ✅ Known base symbols supported by Polygon
POLYGON_SUPPORTED = {
    "BTC", "ETH", "ADA", "XRP", "SOL", "DOGE", "AVAX", "MATIC", "LTC", "DOT",
    "TRX", "LINK", "BCH", "SHIB", "UNI", "XLM", "ATOM", "ETC", "NEAR", "FIL"
}


def fetch_mexc_symbols():
    """Fetch only MEXC symbols supported by Polygon."""
    url = "https://api.mexc.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        symbols = [
            s['symbol'] for s in data['symbols']
            if s['quoteAsset'] == 'USDT'
            and s['isSpotTradingAllowed']
            and s['baseAsset'] in POLYGON_SUPPORTED
        ]
        return sorted(symbols)
    except Exception as e:
        print(f"[ERROR] Could not fetch symbols: {e}")
        return []


def convert_to_polygon_format(mexc_symbol):
    """e.g., BTCUSDT → X:BTCUSD"""
    if not mexc_symbol.endswith("USDT"):
        return None
    base = mexc_symbol.replace("USDT", "")
    return f"X:{base}USD"

def get_all_usdt_symbols():
    res = safe_get("https://api.mexc.com/api/v3/exchangeInfo")
    if not res:
        return []

    data = res.json()
    
    # Extract eligible symbols
    symbols = []
    for s in data["symbols"]:
        base = s["baseAsset"].upper()
        if (
            s["quoteAsset"] == "USDT"
            and s.get("isSpotTradingAllowed", False)  # safer than 'status'
            and base in POLYGON_SUPPORTED
        ):
            symbols.append(s["symbol"])

    print("[DEBUG] All eligible USDT symbols:", symbols)
    return symbols


def get_top_usdt_symbols(limit=5):
    """Fetch top-volume USDT pairs from MEXC, filter Polygon-compatible ones."""
    res = safe_get("https://api.mexc.com/api/v3/ticker/24hr")
    if not res:
        return []
    tickers = res.json()
    filtered = [
        t for t in tickers
        if t["symbol"].endswith("USDT")
        and float(t["quoteVolume"]) > 1000000
        and t["symbol"].replace("USDT", "") in POLYGON_SUPPORTED
    ]
    sorted_by_volume = sorted(filtered, key=lambda x: float(x["quoteVolume"]), reverse=True)
    return [t["symbol"] for t in sorted_by_volume[:limit]]

def load_data(symbols, start, end, api_key):
    """symbols should already be in Polygon format like X:BTCUSD"""
    data = {}
    for symbol in symbols:
        if not symbol.startswith("X:"):
            print(f"[SKIP] Invalid symbol format: {symbol}")
            continue  # ✅ filter out incorrect ones

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={api_key}"
        response = safe_get(url)

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

            data[symbol] = df  # ✅ store using Polygon format

        except Exception as e:
            print(f"[ERROR] Failed to parse data for {symbol}: {e}")
            continue

    return data

