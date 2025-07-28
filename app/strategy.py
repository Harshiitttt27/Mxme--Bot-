from datetime import datetime, timedelta

def can_enter(symbol, positions, cooldowns, config):
    active_positions = len(positions)
    in_cooldown = symbol in cooldowns and cooldowns[symbol] > datetime.now()
    return symbol not in positions and not in_cooldown and active_positions < config.MAX_CONCURRENT_POSITIONS

def check_exit(entry_price, current_price, state, config):
    change = ((current_price - entry_price) / entry_price) * 100
    if change <= config.DROP_THRESHOLD:
        return "stop_loss"
    if change >= config.RISE_THRESHOLD:
        state['peak'] = max(state.get('peak', current_price), current_price)
        return "trailing"
    if state.get('peak'):
        if current_price <= state['peak'] * (1 - config.TRAILING_STOP / 100):
            return "trailing_exit"
    return None