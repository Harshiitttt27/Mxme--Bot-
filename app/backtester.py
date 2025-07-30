# from datetime import datetime, timedelta
# from app.strategy import check_exit, can_enter
# from app.notifier import notify_buy, notify_sell, notify_summary

# def run_backtest(data, config):
#     balance = config.STARTING_BALANCE
#     positions = {}
#     cooldowns = {}
#     trades = []

#     for symbol, df in data.items():
#         for _, row in df.iterrows():
#             price = row['close']
#             now = row['timestamp']

#             # Clean expired cooldowns
#             cooldowns = {k: v for k, v in cooldowns.items() if v > now}

#             # Entry
#             if can_enter(symbol, positions, cooldowns, config):
#                 quantity = (config.TRADE_AMOUNT * (1 - config.FEE)) / price
#                 positions[symbol] = {
#                     'entry_price': price,
#                     'quantity': quantity,
#                     'entry_time': now,
#                     'peak': price
#                 }
#                 notify_buy(symbol, price, quantity, balance)

#             # Exit
#             if symbol in positions:
#                 state = positions[symbol]
#                 reason = check_exit(state['entry_price'], price, state, config)
#                 if reason in ["stop_loss", "trailing_exit"]:
#                     gross = price * state['quantity']
#                     net = gross * (1 - config.FEE)
#                     cost = state['entry_price'] * state['quantity'] * (1 + config.FEE)
#                     pnl = net - cost
#                     balance += pnl
#                     notify_sell(symbol, state['entry_price'], price, pnl, reason, balance)

#                     trades.append({
#                         'symbol': symbol,
#                         'entry': round(state['entry_price'], 4),
#                         'exit': round(price, 4),
#                         'pnl': round(pnl, 2),
#                         'reason': reason
#                     })
#                     del positions[symbol]
#                     cooldowns[symbol] = now + timedelta(days=config.REBUY_DELAY_DAYS)
#                     notify_summary(trades, balance, config.STARTING_BALANCE)

#     return trades


# def export_backtest(trades, filename="backtest"):
#     import os, json, csv
#     os.makedirs("exports", exist_ok=True)

#     # CSV
#     if not trades:
#         print("[EXPORT] No trades to export.")
#         return
    
#     csv_path = f"exports/{filename}.csv"
#     with open(csv_path, "w", newline='') as f:
#         writer = csv.DictWriter(f, fieldnames=trades[0].keys())
#         writer.writeheader()
#         writer.writerows(trades)

#     # JSON
#     json_path = f"exports/{filename}.json"
#     with open(json_path, "w") as f:
#         json.dump(trades, f, indent=2)

#     return {"csv": csv_path, "json": json_path}
from datetime import datetime, timedelta
from app.strategy import check_exit, can_enter
from app.notifier import notify_buy, notify_sell, notify_summary
import pandas as pd
import numpy as np
from collections import defaultdict

def run_backtest(data, config):
    balance = config.STARTING_BALANCE
    positions = {}
    cooldowns = {}
    trades = []
    equity_curve = []
    daily_returns = {}
    symbol_pnls = defaultdict(list)

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
                        'reason': reason,
                        'date': now.date().isoformat()
                    })
                    symbol_pnls[symbol].append(pnl)
                    cooldowns[symbol] = now + timedelta(days=config.REBUY_DELAY_DAYS)
                    notify_summary(trades, balance, config.STARTING_BALANCE)
                    del positions[symbol]

            equity_curve.append((now, balance))
            daily_returns[now.date()] = balance

    # ➕ Metrics Calculation
    pnl_series = pd.Series([p['pnl'] for p in trades])
    dates = [pd.to_datetime(p['date']) for p in trades]
    pnl_df = pd.DataFrame({'date': dates, 'pnl': pnl_series})
    monthly = pnl_df.groupby(pnl_df['date'].dt.to_period('M'))['pnl'].sum().to_dict()


    # Sharpe Ratio
    equity_df = pd.DataFrame(equity_curve, columns=["timestamp", "balance"]).set_index("timestamp")
    equity_df = equity_df.resample('1D').last().ffill()
    equity_df['returns'] = equity_df['balance'].pct_change()
    sharpe = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252) if len(equity_df) > 1 else 0

    # Max Drawdown
    equity_df['peak'] = equity_df['balance'].cummax()
    equity_df['drawdown'] = (equity_df['balance'] - equity_df['peak']) / equity_df['peak']
    max_drawdown = equity_df['drawdown'].min()
    drawdown_series = equity_df.reset_index()[['timestamp', 'drawdown']]
    drawdown_series['timestamp'] = drawdown_series['timestamp'].astype(str)  # 🔥 Fix here

    
    # Heatmap: monthly PnL per symbol
    heatmap_df = pnl_df.copy()
    heatmap_df['symbol'] = [p['symbol'] for p in trades]
    heatmap_df['month'] = heatmap_df['date'].dt.to_period('M')
    heatmap_pivot = heatmap_df.pivot_table(index='month', columns='symbol', values='pnl', aggfunc='sum').fillna(0)
    heatmap = heatmap_pivot.round(2).astype(float).to_dict(orient='index')

    return {
    "trades": trades,
    "metrics": {
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "monthly_returns": {str(k): round(v, 2) for k, v in monthly.items()},
        "symbol_stats": {sym: round(sum(pnls), 2) for sym, pnls in symbol_pnls.items()},
        "drawdown_series": drawdown_series.to_dict(orient='records'),
        "heatmap": {str(k): v for k, v in heatmap.items()}  # ✅ Fix added here
    }
}

def export_backtest(result, filename="backtest"):
    import os, json, csv
    os.makedirs("exports", exist_ok=True)

    trades = result.get("trades", [])
    metrics = result.get("metrics", {})

    if not trades:
        print("[EXPORT] No trades to export.")
        return

    csv_path = f"exports/{filename}.csv"
    with open(csv_path, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)

    json_path = f"exports/{filename}.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    return {"csv": csv_path, "json": json_path}
