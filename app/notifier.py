import requests
from app.config import Config

def send_alert(message):
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})

