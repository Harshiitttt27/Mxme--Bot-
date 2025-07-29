
import requests
import time

def safe_get(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response
            print(f"[WARN] Bad status {response.status_code}, retrying...")
        except Exception as e:
            print(f"[ERROR] Exception during GET: {e}")
        time.sleep(delay)
    return None
