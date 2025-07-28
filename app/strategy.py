from datetime import datetime, timedelta

def can_enter(symbol, positions, cooldowns, config):
    active_positions = len(positions)
    in_cooldown = symbol in cooldowns and cooldowns[symbol] > datetime.now()
    return symbol not in positions and not in_cooldown and active_positions < config.MAX_CONCURRENT_POSITIONS

from datetime import datetime

def check_exit(entry_price, current_price, state, config, symbol=None, notify=None):
    """
    Checks if a position should be exited or modified based on current price.
    
    Args:
        entry_price (float): The entry price of the position.
        current_price (float): The latest price.
        state (dict): Position state (e.g. 'peak', 'trailing_active').
        config (Config): Config object.
        symbol (str): (Optional) Symbol name for logging.
        notify (func): (Optional) Callback to send alerts (e.g. Telegram).
    
    Returns:
        str | None: Reason for exit or action taken (e.g. 'stop_loss', 'trailing_exit', 'trailing_activated'), or None.
    """

    change = ((current_price - entry_price) / entry_price) * 100

    # 1. Stop-loss check
    if change <= config.DROP_THRESHOLD:
        if notify:
            notify(f"🔻 STOP LOSS TRIGGERED for {symbol} | Entry: {entry_price:.2f} → Current: {current_price:.2f} ({change:.2f}%)")
        return "stop_loss"

    # 2. Rise threshold check
    if change >= config.RISE_THRESHOLD:
        if not state.get('trailing_active'):
            # First time rise threshold hit — activate trailing
            state['peak'] = current_price
            state['trailing_active'] = True
            if notify:
                notify(f"📈 RISE THRESHOLD REACHED for {symbol} @ {current_price:.2f} (+{change:.2f}%) → Trailing Stop Activated")
            return "trailing_activated"
        else:
            # Trailing active, update peak if current price is higher
            state['peak'] = max(state['peak'], current_price)

    # 3. Trailing stop check
    if state.get('trailing_active'):
        trailing_limit = state['peak'] * (1 - config.TRAILING_STOP / 100)
        if current_price <= trailing_limit:
            if notify:
                drop_from_peak = ((current_price - state['peak']) / state['peak']) * 100
                notify(f"🔻 TRAILING STOP EXIT for {symbol} | Peak: {state['peak']:.2f} → Current: {current_price:.2f} ({drop_from_peak:.2f}%)")
            return "trailing_exit"

    # No exit condition met
    return None
