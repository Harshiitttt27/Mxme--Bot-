from datetime import datetime, timedelta
from app.strategy import check_exit, can_enter

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
                continue

            # Exit
            if symbol in positions:
                state = positions[symbol]
                reason = check_exit(state['entry_price'], price, state, config)
                if reason in ["stop_loss", "trailing_exit"]:
                    gross = price * state['quantity']
                    net = gross * (1 - config.FEE)
                    cost = state['entry_price'] * state['quantity'] * (1 + config.FEE)
                    pnl = net - cost
                    trades.append({
                        'symbol': symbol,
                        'entry': round(state['entry_price'], 4),
                        'exit': round(price, 4),
                        'pnl': round(pnl, 2),
                        'reason': reason
                    })
                    del positions[symbol]
                    cooldowns[symbol] = now + timedelta(days=config.REBUY_DELAY_DAYS)
    return trades