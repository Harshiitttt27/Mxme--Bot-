# # FILE: app/mexc_live.py

# import requests
# import time
# import hmac
# import hashlib
# import uuid
# from datetime import datetime
# from app.config import Config

# # Position tracking
# live_positions = {}       # symbol: {entry_price, qty, time}
# live_trades = [] 
# SAFE_MODE = True  # ⛔ Flip to False for real trading


# def sign_request(secret, query_string):
#     return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# def place_market_order(api_key, secret, symbol, side, quantity):
#     if SAFE_MODE:
#         fake_price = get_price(symbol)
#         log_trade(symbol, side, quantity, fake_price, f"SIMULATED")
#         return {"simulated": True, "price": fake_price}
    
#     url = "https://api.mexc.com/api/v3/order"
#     timestamp = int(time.time() * 1000)
#     params = {
#         "symbol": symbol,
#         "side": side.upper(),  # BUY or SELL
#         "type": "MARKET",
#         "quantity": quantity,
#         "timestamp": timestamp,
#         "recvWindow": 5000
#     }

#     query = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
#     signature = sign_request(secret, query)
#     headers = {"X-MEXC-APIKEY": api_key}
    
#     final_url = f"{url}?{query}&signature={signature}"
#     response = requests.post(final_url, headers=headers)
#     res = response.json()

#     if response.status_code == 200 and res.get("status") == "FILLED":
#         log_trade(symbol, side, quantity, res['fills'][0]['price'], res)
#     return res

# def get_price(symbol):
#     url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
#     res = requests.get(url)
#     return float(res.json()['price'])

# def log_trade(symbol, side, qty, price, response):
#     trade = {
#         "symbol": symbol,
#         "side": side,
#         "quantity": float(qty),
#         "price": float(price),
#         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         "response": str(response)
#     }
#     live_trades.append(trade)

#     if side.upper() == "BUY":
#         live_positions[symbol] = {
#             "entry_price": float(price),
#             "quantity": float(qty),
#             "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }
#     elif side.upper() == "SELL" and symbol in live_positions:
#         del live_positions[symbol]

# import csv
# import json
# import os

# EXPORT_DIR = "exports"

# def export_live_trades_csv():
#     if not live_trades:
#         print("[EXPORT] No live trades to export.")
#         return None  # gracefully handle no data
#     filepath = os.path.join(EXPORT_DIR, "live_trades.csv")
#     with open(filepath, "w", newline='') as f:
#         writer = csv.DictWriter(f, fieldnames=live_trades[0].keys())
#         writer.writeheader()
#         writer.writerows(live_trades)
#     return filepath

# def export_live_trades_json():
#     if not live_trades:
#         print("[EXPORT] No live trades to export.")
#         return None
#     filepath = os.path.join(EXPORT_DIR, "live_trades.json")
#     with open(filepath, "w") as f:
#         json.dump(live_trades, f, indent=2)
#     return filepath
# FILE: app/mexc_live.py

import requests
import time
import hmac
import hashlib
from datetime import datetime
from app.config import Config
from app.notifier import notify_live_buy, notify_live_sell  # ✅ add this import
# Position tracking
live_positions = {}  # symbol: {entry_price, qty, time}
live_trades = []

SAFE_MODE = True  # ⛔ Flip to False for real trading


def sign_request(secret, query_string):
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def get_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(f"[ERROR] Failed to fetch price for {symbol}: {e}")
        return None


def place_market_order(api_key, secret, symbol, side, quantity):
    if SAFE_MODE:
        fake_price = get_price(symbol)
        if fake_price is None:
            return {"error": f"Could not fetch price for {symbol}"}
        log_trade(symbol, side, quantity, fake_price, "SIMULATED")
        return {"simulated": True, "price": fake_price}

    url = "https://api.mexc.com/api/v3/order"
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "side": side.upper(),  # BUY or SELL
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": timestamp,
        "recvWindow": 5000
    }

    query = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = sign_request(secret, query)
    headers = {"X-MEXC-APIKEY": api_key}

    final_url = f"{url}?{query}&signature={signature}"
    response = requests.post(final_url, headers=headers)

    try:
        res = response.json()
    except Exception as e:
        return {"error": f"Failed to parse MEXC response: {e}"}

    if response.status_code == 200 and res.get("status") == "FILLED":
        filled_price = float(res['fills'][0]['price']) if res.get('fills') else get_price(symbol)
        log_trade(symbol, side, quantity, filled_price, res)
    else:
        print(f"[ERROR] MEXC order failed: {res}")

    return res


def log_trade(symbol, side, qty, price, response):
    if price is None:
        print(f"[WARN] Cannot log trade for {symbol} – price missing.")
        return

    trade = {
        "symbol": symbol,
        "side": side,
        "quantity": float(qty),
        "price": float(price),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "response": str(response)
    }
    live_trades.append(trade)

    if side.upper() == "BUY":
        live_positions[symbol] = {
            "entry_price": float(price),
            "quantity": float(qty),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        notify_live_buy(symbol, price, qty)  # ✅ Telegram notify
    elif side.upper() == "SELL" and symbol in live_positions:
        del live_positions[symbol]
        notify_live_sell(symbol, price, qty, reason="Manual or trailing exit")  # ✅ Telegram notify

# CSV / JSON Export for live trades
import csv
import json
import os


def export_live_trades_csv():
    if not live_trades:
        return None

    filename = "live_trades.csv"
    filepath = os.path.join("exports", filename)
    os.makedirs("exports", exist_ok=True)

    with open(filepath, "w", newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=live_trades[0].keys())
        writer.writeheader()
        for trade in live_trades:
            writer.writerow(trade)

    return filepath


def export_live_trades_json():
    if not live_trades:
        return None

    filename = "live_trades.json"
    filepath = os.path.join("exports", filename)
    os.makedirs("exports", exist_ok=True)

    with open(filepath, "w") as jsonfile:
        json.dump(live_trades, jsonfile, indent=2)

    return filepath
