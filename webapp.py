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

app = Flask(__name__)

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
        for symbol in list(positions.keys()):
            pos = positions[symbol]
            price = price_dict[symbol]
            reason = check_exit(pos['entry_price'], price, pos, config, symbol)

            if reason in ["stop_loss", "trailing_exit"]:
                net = price * pos['quantity'] * (1 - config.FEE)
                config.balance += net
                cooldowns[symbol] = datetime.now() + timedelta(days=config.REBUY_DELAY_DAYS)
                del positions[symbol]
                print(f"[SELL] {symbol} due to {reason} @ ${price:.2f}")

        # 2. Entries
        for symbol in symbols:
            price = price_dict[symbol]
            try_enter_position(symbol, price, positions, cooldowns, config, position_queue)

        # 3. Process queue
        for symbol in position_queue[:]:
            price = price_dict[symbol]
            success, msg = try_enter_position(symbol, price, positions, cooldowns, config, position_queue)
            if success:
                position_queue.remove(symbol)
                print("[QUEUE FILLED]", msg)
        
        # 4. Rebuy notifications
        # Track cooldown expiry notifications to avoid spamming
        notified_rebuy = set()  # Track symbols whose cooldown expiry has been notified
        for symbol, cooldown in cooldowns.items():
            if cooldown <= datetime.now() and symbol not in notified_rebuy:
                send_alert(f"🔄 {symbol} is ready for rebuy after cooldown.")
                notified_rebuy.add(symbol)

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
        app.monitor_started = True  # prevent multiple threads




if __name__ == "__main__":
    app.run(debug=True)
