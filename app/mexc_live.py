# FILE: app/mexc_live.py

import requests
import time
import hmac
import hashlib
import uuid
from datetime import datetime
from app.config import Config

# Position tracking
live_positions = {}       # symbol: {entry_price, qty, time}
live_trades = [] 
SAFE_MODE = True  # ⛔ Flip to False for real trading


def sign_request(secret, query_string):
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def place_market_order(api_key, secret, symbol, side, quantity):
    if SAFE_MODE:
        fake_price = get_price(symbol)
        log_trade(symbol, side, quantity, fake_price, f"SIMULATED")
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
    res = response.json()

    if response.status_code == 200 and res.get("status") == "FILLED":
        log_trade(symbol, side, quantity, res['fills'][0]['price'], res)
    return res

def get_price(symbol):
    url = f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}"
    res = requests.get(url)
    return float(res.json()['price'])

def log_trade(symbol, side, qty, price, response):
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
    elif side.upper() == "SELL" and symbol in live_positions:
        del live_positions[symbol]

import csv
import json
import os

EXPORT_DIR = "exports"

def export_live_trades_csv():
    filepath = os.path.join(EXPORT_DIR, "live_trades.csv")
    with open(filepath, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=live_trades[0].keys())
        writer.writeheader()
        writer.writerows(live_trades)
    return filepath

def export_live_trades_json():
    filepath = os.path.join(EXPORT_DIR, "live_trades.json")
    with open(filepath, "w") as f:
        json.dump(live_trades, f, indent=2)
    return filepath
