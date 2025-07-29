from flask import Flask, render_template, request
from app.backtester import run_backtest
from app.data_manager import load_data
from app.config import Config
import threading
import time
from datetime import datetime, timedelta
from app.config import Config
from app.notifier import send_alert
from app.strategy import try_enter_position, check_exit
import random
import threading
from flask import send_file
from app.mexc_live import export_live_trades_csv, export_live_trades_json


lock = threading.Lock()


app = Flask(__name__)
notified_rebuy = set()


@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        symbols = request.form['symbols'].split(',')
        start = request.form['start_date']
        end = request.form['end_date']
        api_key = request.form['api_key']
        balance = float(request.form['starting_balance'])

        config = Config()
        config.POLYGON_API_KEY = api_key
        config.STARTING_BALANCE = balance

        data = load_data(symbols, start, end, api_key)
        results = run_backtest(data, config)
        from app.backtester import export_backtest
        export_backtest(results)

    return render_template('index.html', results=results)


config = Config()

# Simulated data
positions = {}
cooldowns = {}
position_queue = []

# Replace with real price API
def get_live_price(symbol):
    return round(100 + random.uniform(-2, 2), 2)

# reason = check_exit(
#     pos['entry_price'],
#     price,
#     pos,
#     config,
#     symbol,
#     notify=send_alert
# )

def monitor_loop():
    symbols = ["BTC", "ETH", "ADA", "XRP", "SOL"]
    while True:
        price_dict = {s: get_live_price(s) for s in symbols}

        # 1. Exits
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
                    send_alert(f"[SELL] {symbol} @ ${price:.2f} due to {reason}. Balance: ${config.balance:.2f}")

        # 2. Entries
        with lock:
            for symbol in symbols:
                price = price_dict[symbol]
                try_enter_position(symbol, price, positions, cooldowns, config, position_queue)

        # 3. Process queue
        with lock:
            for symbol in position_queue[:]:
                price = price_dict[symbol]
                success, msg = try_enter_position(symbol, price, positions, cooldowns, config, position_queue)
                if success:
                    position_queue.remove(symbol)
                    print("[QUEUE FILLED]", msg)

        # 4. Rebuy notifications
        with lock:
            for symbol, cooldown in cooldowns.items():
                if cooldown <= datetime.now() and symbol not in notified_rebuy:
                    send_alert(f"🔄 {symbol} is ready for rebuy after cooldown.")
                    notified_rebuy.add(symbol)

        # 5. Debug: Cooldown Status
        with lock:
            for symbol, expiry in cooldowns.items():
                print(f"[COOLDOWN] {symbol} expires at {expiry}")

        with lock:
            print(f"[INFO] Balance: ${config.balance:.2f} | Positions: {len(positions)} | Queue: {position_queue}")
        
        time.sleep(120)

@app.before_request
def start_monitoring():
    if not hasattr(app, 'monitor_started'):
        t = threading.Thread(target=monitor_loop)
        t.daemon = True
        t.start()
        app.monitor_started = True  # prevent multiple threads

from app.mexc_live import place_market_order, get_price

from app.mexc_live import place_market_order, get_price, live_positions, live_trades

@app.route('/live', methods=['GET', 'POST'])
def live_trading():
    message = ""
    if request.method == 'POST':
        symbol = request.form['symbol'].strip().upper()
        quantity = request.form['quantity']
        side = request.form['side']

        try:
            result = place_market_order(config.MEXC_API_KEY, config.MEXC_SECRET_KEY, symbol, side, quantity)
            message = f"Order Executed: {result}"
        except Exception as e:
            message = f"Error: {e}"

    return render_template(
        'live.html',
        message=message,
        positions=live_positions,
        trades=live_trades
    )

@app.route("/live/export", methods=["POST"])
def export_live():
    format = request.form['format']
    if format == "csv":
        filepath = export_live_trades_csv()
    else:
        filepath = export_live_trades_json()
    
    if not filepath:
        return "⚠️ No trades available to export.", 400
    
    return send_file(filepath, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
