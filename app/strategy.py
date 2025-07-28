from datetime import datetime, timedelta

def can_enter(symbol, positions, cooldowns, config):
    active_positions = len(positions)
    in_cooldown = symbol in cooldowns and cooldowns[symbol] > datetime.now()
    return symbol not in positions and not in_cooldown and active_positions < config.MAX_CONCURRENT_POSITIONS

def check_exit(entry_price, current_price, state, config):
    change = ((current_price - entry_price) / entry_price) * 100

    # Stop-loss check
    if change <= config.DROP_THRESHOLD:
        return "stop_loss"

    # First time rise threshold hit → activate trailing
    if change >= config.RISE_THRESHOLD:
        if 'peak' not in state or state['peak'] is None:
            state['peak'] = current_price  # First activation
            state['trailing_active'] = True
            return "trailing_activated"
        else:
            # Update peak if price keeps rising
            state['peak'] = max(state['peak'], current_price)

    # Check trailing stop if activated
    if state.get('trailing_active'):
        if current_price <= state['peak'] * (1 - config.TRAILING_STOP / 100):
            return "trailing_exit"

    return None
