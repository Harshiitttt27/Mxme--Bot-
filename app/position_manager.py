# FILE: app/position_manager.py

from datetime import datetime, timedelta
import uuid

def try_enter_position(symbol, price, positions, cooldowns, config, position_queue):
    now = datetime.now()

    # Clean expired cooldowns
    cooldowns = {k: v for k, v in cooldowns.items() if v > now}

    # Entry Conditions
    if symbol in positions or (symbol in cooldowns and cooldowns[symbol] > now):
        return False, "Already in position or cooldown"

    if len(positions) >= config.MAX_CONCURRENT_POSITIONS:
        if symbol not in position_queue:
            position_queue.append(symbol)
        return False, f"Max positions reached — {symbol} queued"

    # Check balance
    estimated_cost = config.TRADE_AMOUNT * (1 + config.FEE)
    if config.balance < estimated_cost:
        return False, f"Insufficient balance for {symbol}"

    # Simulate Buy
    fee = config.FEE
    quantity = (config.TRADE_AMOUNT * (1 - fee)) / price
    order_id = str(uuid.uuid4())

    positions[symbol] = {
        "entry_price": price,
        "quantity": quantity,
        "entry_time": now,
        "order_id": order_id,
        "peak": price,
        "trailing_active": False
    }

    config.balance -= estimated_cost
    print(f"[BUY] {symbol} @ ${price:.2f} | Qty: {quantity:.5f} | OrderID: {order_id}")
    return True, f"Entered {symbol}"

def check_queue_for_entry(price_dict, position_queue, positions, cooldowns, config):
    for symbol in position_queue[:]:  # copy to avoid modification during iteration
        price = price_dict.get(symbol)
        if not price:
            continue
        success, msg = try_enter_position(symbol, price, positions, cooldowns, config, position_queue)
        if success:
            position_queue.remove(symbol)
            print("[QUEUE FILLED]", msg)

def check_exit(entry_price, current_price, state, config, symbol=None):
    change = ((current_price - entry_price) / entry_price) * 100

    if change <= config.DROP_THRESHOLD:
        return "stop_loss"

    if change >= config.RISE_THRESHOLD:
        if not state.get('trailing_active'):
            state['peak'] = current_price
            state['trailing_active'] = True
            return "trailing_activated"
        else:
            state['peak'] = max(state['peak'], current_price)

    if state.get('trailing_active'):
        if current_price <= state['peak'] * (1 - config.TRAILING_STOP / 100):
            return "trailing_exit"

    return None

def try_exit_position(symbol, price, positions, cooldowns, config, send_alert):
    pos = positions[symbol]
    reason = check_exit(pos['entry_price'], price, pos, config, symbol, send_alert)
    if reason in ["stop_loss", "trailing_exit"]:
        gross = price * pos['quantity']
        net = gross * (1 - config.FEE)
        config.balance += net
        cooldowns[symbol] = datetime.now() + timedelta(days=config.REBUY_DELAY_DAYS)
        del positions[symbol]
        send_alert(f"[SELL] {symbol} @ ${price:.2f} due to {reason}. Balance: ${config.balance:.2f}")

