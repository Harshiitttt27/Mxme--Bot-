# from flask import Flask, render_template, request
# from app.backtester import run_backtest
# from app.data_manager import load_data
# from app.config import Config
# import threading
# import time
# from datetime import datetime, timedelta
# from app.config import Config
# from app.notifier import send_alert
# from app.strategy import try_enter_position, check_exit
# import random
# import threading
# from flask import send_file
# from app.mexc_live import export_live_trades_csv, export_live_trades_json


# lock = threading.Lock()


# app = Flask(__name__)
# notified_rebuy = set()


# @app.route('/', methods=['GET', 'POST'])
# def index():
#     results = []
#     if request.method == 'POST':
#         symbols = request.form['symbols'].split(',')
#         start = request.form['start_date']
#         end = request.form['end_date']
#         api_key = request.form['api_key']
#         balance = float(request.form['starting_balance'])

#         config = Config()
#         config.POLYGON_API_KEY = api_key
#         config.STARTING_BALANCE = balance

#         data = load_data(symbols, start, end, api_key)
#         results = run_backtest(data, config)
#         from app.backtester import export_backtest
#         export_backtest(results)

#     return render_template('index.html', results=results)


# config = Config()

# # Simulated data
# positions = {}
# cooldowns = {}
# position_queue = []

# # Replace with real price API
# def get_live_price(symbol):
#     return round(100 + random.uniform(-2, 2), 2)

# # reason = check_exit(
# #     pos['entry_price'],
# #     price,
# #     pos,
# #     config,
# #     symbol,
# #     notify=send_alert
# # )

# def monitor_loop():
#     symbols = ["BTC", "ETH", "ADA", "XRP", "SOL"]
#     while True:
#         price_dict = {s: get_live_price(s) for s in symbols}

#         # 1. Exits
#         with lock:
#             for symbol in list(positions.keys()):
#                 pos = positions[symbol]
#                 price = price_dict[symbol]
#                 reason = check_exit(pos['entry_price'], price, pos, config, symbol, notify=send_alert)

#                 if reason in ["stop_loss", "trailing_exit"]:
#                     net = price * pos['quantity'] * (1 - config.FEE)
#                     config.balance += net
#                     cooldowns[symbol] = datetime.now() + timedelta(days=config.REBUY_DELAY_DAYS)
#                     del positions[symbol]
#                     send_alert(f"[SELL] {symbol} @ ${price:.2f} due to {reason}. Balance: ${config.balance:.2f}")

#         # 2. Entries
#         with lock:
#             for symbol in symbols:
#                 price = price_dict[symbol]
#                 try_enter_position(symbol, price, positions, cooldowns, config, position_queue)

#         # 3. Process queue
#         with lock:
#             for symbol in position_queue[:]:
#                 price = price_dict[symbol]
#                 success, msg = try_enter_position(symbol, price, positions, cooldowns, config, position_queue)
#                 if success:
#                     position_queue.remove(symbol)
#                     print("[QUEUE FILLED]", msg)

#         # 4. Rebuy notifications
#         with lock:
#             for symbol, cooldown in cooldowns.items():
#                 if cooldown <= datetime.now() and symbol not in notified_rebuy:
#                     send_alert(f"🔄 {symbol} is ready for rebuy after cooldown.")
#                     notified_rebuy.add(symbol)

#         # 5. Debug: Cooldown Status
#         with lock:
#             for symbol, expiry in cooldowns.items():
#                 print(f"[COOLDOWN] {symbol} expires at {expiry}")

#         with lock:
#             print(f"[INFO] Balance: ${config.balance:.2f} | Positions: {len(positions)} | Queue: {position_queue}")
        
#         time.sleep(120)

# @app.before_request
# def start_monitoring():
#     if not hasattr(app, 'monitor_started'):
#         t = threading.Thread(target=monitor_loop)
#         t.daemon = True
#         t.start()
#         app.monitor_started = True  # prevent multiple threads

# from app.mexc_live import place_market_order, get_price

# from app.mexc_live import place_market_order, get_price, live_positions, live_trades

# @app.route('/live', methods=['GET', 'POST'])
# def live_trading():
#     message = ""
#     if request.method == 'POST':
#         symbol = request.form['symbol'].strip().upper()
#         quantity = request.form['quantity']
#         side = request.form['side']

#         try:
#             result = place_market_order(config.MEXC_API_KEY, config.MEXC_SECRET_KEY, symbol, side, quantity)
#             message = f"Order Executed: {result}"
#         except Exception as e:
#             message = f"Error: {e}"

#     return render_template(
#         'live.html',
#         message=message,
#         positions=live_positions,
#         trades=live_trades
#     )

# @app.route("/live/export", methods=["POST"])
# def export_live():
#     format = request.form['format']
#     if format == "csv":
#         filepath = export_live_trades_csv()
#     else:
#         filepath = export_live_trades_json()
    
#     if not filepath:
#         return "⚠️ No trades available to export.", 400
    
#     return send_file(filepath, as_attachment=True)



# if __name__ == "__main__":
#     app.run(debug=True)

from flask import Flask, render_template, request, send_file, make_response, session
from app.backtester import run_backtest, export_backtest
from app.data_manager import load_data
from app.config import Config
from app.notifier import notify_live_sell, send_alert
from app.strategy import try_enter_position, check_exit
from app.mexc_live import (
    export_live_trades_csv, export_live_trades_json,
    place_market_order, get_price, live_positions, live_trades
)

import threading
import time
import random
import csv
import json
from datetime import datetime, timedelta
from io import StringIO
from app.notifier import send_alert, notify_live_buy  # 👈 add this import
from app.data_manager import load_data, fetch_mexc_symbols, convert_to_polygon_format
from app.data_manager import get_all_usdt_symbols, get_top_usdt_symbols

# Initialize Flask
app = Flask(__name__)
app.secret_key = "random-secure-key"  # Needed for session

lock = threading.Lock()
notified_rebuy = set()
positions = {}
cooldowns = {}
position_queue = []
config = Config()


# ------------ BACKTEST ROUTES ------------
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    metrics = {}
    if request.method == 'POST':
        mode = request.form.get("symbol_mode", "custom")
        start = request.form['start_date']
        end = request.form['end_date']
        api_key = request.form['api_key']
        balance = float(request.form['starting_balance'])

        config.POLYGON_API_KEY = api_key
        config.STARTING_BALANCE = balance

        # Symbol selection
        if mode == "all":
            selected = get_all_usdt_symbols()
        elif mode == "top":
            selected = get_top_usdt_symbols(limit=5)
        else:
            custom_input = request.form.get("symbols", "")
            selected = [s.strip().upper() for s in custom_input.split(",") if s.strip()]

        # ✅ Convert to polygon symbols
        polygon_symbols = []
        for s in selected:
            if s.startswith("X:"):
                polygon_symbols.append(s)
            else:
                conv = convert_to_polygon_format(s)
                if conv:
                    polygon_symbols.append(conv)

        print("[INFO] Final Polygon Symbols Used:", polygon_symbols)

        # Load data and run backtest
        data = load_data(polygon_symbols, start, end, api_key)
        result = run_backtest(data, config)  # 🔁 returns dict with trades & metrics
        export_backtest(result)

        results = result.get("trades", [])
        metrics = result.get("metrics", {})

        session["results"] = results
        session["metrics"] = metrics

    return render_template("index.html", results=results, metrics=metrics, positions=None, trades=None, message=None)

@app.route("/download-csv")
def download_csv():
    results = session.get("results")
    if not results:
        return "⚠️ No results to export", 400

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["symbol", "entry", "exit", "pnl", "reason"])
    writer.writeheader()
    for row in results:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=backtest_results.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@app.route("/download-json")
def download_json():
    results = session.get("results")
    if not results:
        return "⚠️ No results to export", 400

    response = make_response(json.dumps(results, indent=2))
    response.headers["Content-Disposition"] = "attachment; filename=backtest_results.json"
    response.headers["Content-Type"] = "application/json"
    return response


# ------------ LIVE TRADING ROUTES ------------

@app.route('/live', methods=['GET', 'POST'])
def live_trading():
    message = ""
    session.pop("results", None)  # Clear previous backtest results when switching to live

    if request.method == 'POST' and request.form.get("form_type") == "live":
        try:
            symbol = request.form.get('symbol', '').strip().upper()
            quantity = request.form.get('quantity', '')
            side = request.form.get('side', '')

            if not symbol or not quantity or not side:
                message = "⚠️ Missing required fields."
            else:
                result = place_market_order(config.MEXC_API_KEY, config.MEXC_SECRET_KEY, symbol, side, quantity)
                message = f"✅ Order Executed: {result}"

        except Exception as e:
            message = f"❌ Error: {e}"

        session['live_trades'] = live_trades

    return render_template(
        'index.html',
        message=message,
        positions=live_positions,
        trades=live_trades,
        results=session.get('results', [])  # still show empty results array
    )

@app.route("/download-live-csv")
def download_live_csv():
    trades = session.get("live_trades")
    if not trades:
        return "⚠️ No live trades to export", 400

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=trades[0].keys())
    writer.writeheader()
    for trade in trades:
        writer.writerow(trade)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=live_trades.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@app.route("/download-live-json")
def download_live_json():
    trades = session.get("live_trades")
    if not trades:
        return "⚠️ No live trades to export", 400

    response = make_response(json.dumps(trades, indent=2))
    response.headers["Content-Disposition"] = "attachment; filename=live_trades.json"
    response.headers["Content-Type"] = "application/json"
    return response


# ------------ SIMULATED MONITORING LOOP ------------

def get_live_price(symbol):
    return round(100 + random.uniform(-2, 2), 2)

def monitor_loop():
    symbols = ["BTC", "ETH", "ADA", "XRP", "SOL"]
    while True:
        price_dict = {s: get_live_price(s) for s in symbols}

        with lock:
            for symbol in list(positions.keys()):
                pos = positions[symbol]
                price = price_dict[symbol]
                reason = check_exit(pos['entry_price'], price, pos, config, symbol, notify=send_alert)

                if reason in ["stop_loss", "trailing_exit"]:
                    net = price * pos['quantity'] * (1 - config.FEE)
                    config.balance += net
                    cooldowns[symbol] = datetime.now() + timedelta(days=config.REBUY_DELAY_DAYS)
                    del positions[symbol]
                    notify_live_sell(symbol, price, pos['quantity'], reason)


        with lock:
            for symbol in symbols:
                price = price_dict[symbol]
                try_enter_position(symbol, price, positions, cooldowns, config, position_queue)

        with lock:
            for symbol in position_queue[:]:
                price = price_dict[symbol]
                success, msg = try_enter_position(symbol, price, positions, cooldowns, config, position_queue)
                if success:
                    position_queue.remove(symbol)
                    print("[QUEUE FILLED]", msg)

        with lock:
            for symbol, cooldown in cooldowns.items():
                if cooldown <= datetime.now() and symbol not in notified_rebuy:
                    send_alert(f"🔄 {symbol} is ready for rebuy after cooldown.")
                    notified_rebuy.add(symbol)

        with lock:
            for symbol, expiry in cooldowns.items():
                print(f"[COOLDOWN] {symbol} expires at {expiry}")

            print(f"[INFO] Balance: ${config.balance:.2f} | Positions: {len(positions)} | Queue: {position_queue}")

        time.sleep(120)


@app.before_request
def start_monitoring():
    if not hasattr(app, 'monitor_started'):
        t = threading.Thread(target=monitor_loop)
        t.daemon = True
        t.start()
        app.monitor_started = True


# ------------ RUN APP ------------
if __name__ == "__main__":
    app.run(debug=True)
