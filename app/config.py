import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", 100))
    FEE = float(os.getenv("FEE", 0.1)) / 100
    RISE_THRESHOLD = float(os.getenv("RISE_THRESHOLD", 3.0))
    DROP_THRESHOLD = float(os.getenv("DROP_THRESHOLD", -0.5))
    TRAILING_STOP = 0.5
    REBUY_DELAY_DAYS = int(os.getenv("REBUY_DELAY_DAYS", 5))
    MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT_POSITIONS", 5))
    STARTING_BALANCE = float(os.getenv("STARTING_BALANCE", 10000))