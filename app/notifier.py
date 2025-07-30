import requests
from app.config import Config

def send_alert(message):
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        print("[ALERT]", message)
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": message})
    except Exception as e:
        print("[TELEGRAM ERROR]", e)

def notify_buy(symbol, price, quantity, balance):
    send_alert(
        f"🟢 *BUY EXECUTED*\n"
        f"• Symbol: `{symbol}`\n"
        f"• Price: ${price:.2f}\n"
        f"• Quantity: {quantity:.4f}\n"
        f"• Balance: ${balance:.2f}"
    )

def notify_sell(symbol, entry_price, exit_price, pnl, reason, balance):
    emoji = "✅" if pnl >= 0 else "🔻"
    send_alert(
        f"{emoji} *SELL EXECUTED*\n"
        f"• Symbol: `{symbol}`\n"
        f"• Entry → Exit: ${entry_price:.2f} → ${exit_price:.2f}\n"
        f"• PnL: ${pnl:.2f} ({reason})\n"
        f"• Balance: ${balance:.2f}"
    )

def notify_trailing(symbol, peak, current):
    send_alert(
        f"📈 *TRAILING STOP ACTIVATED*\n"
        f"{symbol} hit +{((peak - current)/current)*100:.2f}%\n"
        f"Peak: ${peak:.2f} | Current: ${current:.2f}"
    )

def notify_summary(trades, final_balance, starting_balance):
    if not trades:
        send_alert("No trades were executed during the session.")
        return
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    net_pnl = sum(t['pnl'] for t in trades)
    win_rate = (len(wins) / len(trades)) * 100

    send_alert(
    f"📊 *BACKTEST SUMMARY*\n"
    f"• 📈 Total Trades: {len(trades)}\n"
    f"• 🧠 Win Rate: {win_rate:.1f}%\n"
    f"• 💰 Net PnL: ${net_pnl:.2f}\n"
    f"• 💼 Start → Final Balance: ${starting_balance:.2f} → ${final_balance:.2f}"
)

def notify_live_buy(symbol, price, quantity):
    send_alert(
        f"📢 *LIVE BUY ORDER EXECUTED*\n"
        f"• Symbol: `{symbol}`\n"
        f"• Quantity: {quantity}\n"
        f"• Price: ${price:.2f}"
    )

def notify_live_sell(symbol, price, quantity, reason):
    send_alert(
        f"🔴 *LIVE SELL ORDER EXECUTED*\n"
        f"• Symbol: `{symbol}`\n"
        f"• Quantity: {quantity}\n"
        f"• Price: ${price:.2f}\n"
        f"• Reason: {reason}"
    )
