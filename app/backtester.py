from datetime import datetime, timedelta
from app.strategy import check_exit, can_enter
from app.notifier import notify_buy, notify_sell, notify_summary

def run_backtest(data, config):
    balance = config.STARTING_BALANCE
    positions = {}
    cooldowns = {}
    trades = []

    for symbol, df in data.items():
        for _, row in df.iterrows():
            price = row['close']
            now = row['timestamp']

            # Clean expired cooldowns
            cooldowns = {k: v for k, v in cooldowns.items() if v > now}

            # Entry
            if can_enter(symbol, positions, cooldowns, config):
                quantity = (config.TRADE_AMOUNT * (1 - config.FEE)) / price
                positions[symbol] = {
                    'entry_price': price,
                    'quantity': quantity,
                    'entry_time': now,
                    'peak': price
                }
                notify_buy(symbol, price, quantity, balance)

            # Exit
            if symbol in positions:
                state = positions[symbol]
                reason = check_exit(state['entry_price'], price, state, config)
                if reason in ["stop_loss", "trailing_exit"]:
                    gross = price * state['quantity']
                    net = gross * (1 - config.FEE)
                    cost = state['entry_price'] * state['quantity'] * (1 + config.FEE)
                    pnl = net - cost
                    balance += pnl
                    notify_sell(symbol, state['entry_price'], price, pnl, reason, balance)

                    trades.append({
                        'symbol': symbol,
                        'entry': round(state['entry_price'], 4),
                        'exit': round(price, 4),
                        'pnl': round(pnl, 2),
                        'reason': reason
                    })
                    del positions[symbol]
                    cooldowns[symbol] = now + timedelta(days=config.REBUY_DELAY_DAYS)
                    notify_summary(trades, balance, config.STARTING_BALANCE)

    return trades


def export_backtest(trades, filename="backtest"):
    import os, json, csv
    os.makedirs("exports", exist_ok=True)

    # CSV
    csv_path = f"exports/{filename}.csv"
    with open(csv_path, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)

    # JSON
    json_path = f"exports/{filename}.json"
    with open(json_path, "w") as f:
        json.dump(trades, f, indent=2)

    return {"csv": csv_path, "json": json_path}
