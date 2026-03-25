import os
from dotenv import load_dotenv

load_dotenv(encoding="utf-8-sig")  # utf-8-sig strips Windows BOM automatically

# --- Kalshi API ---
KALSHI_API_KEY_ID = os.getenv("KALSHI_API_KEY_ID", "").strip()
KALSHI_RSA_PRIVATE_KEY_PATH = os.getenv("KALSHI_RSA_PRIVATE_KEY_PATH", "").strip()
KALSHI_BASE_URL = os.getenv("KALSHI_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Whale Detection (Sniper Mode) ---
# A trade is a "whale" if its size is >= this multiplier times the rolling average
# 25x = only truly massive outliers (sniper approach)
WHALE_THRESHOLD_MULTIPLIER = float(os.getenv("WHALE_THRESHOLD_MULTIPLIER", "25"))
# Number of recent trades used to calculate the rolling average
ROLLING_WINDOW_SIZE = int(os.getenv("ROLLING_WINDOW_SIZE", "100"))
# Minimum total dollar size to even consider a trade (filters minnows)
WHALE_MIN_DOLLAR_SIZE = float(os.getenv("WHALE_MIN_DOLLAR_SIZE", "50"))
# Fixed dollar amount for paper copy trades (hypothetical "what if I copied with $X")
PAPER_COPY_AMOUNT_CENTS = int(os.getenv("PAPER_COPY_AMOUNT_CENTS", "1000"))  # $10

# --- Trading ---
# What percentage of your portfolio balance to risk per whale trade (0.15 = 15%)
PORTFOLIO_RISK_FRACTION = float(os.getenv("PORTFOLIO_RISK_FRACTION", "0.15"))
# Minimum trade size in cents to place (avoids dust trades)
MIN_TRADE_SIZE_CENTS = int(os.getenv("MIN_TRADE_SIZE_CENTS", "100"))
# Minimum contract price in cents to copy (filters out near-certain penny bets)
# e.g. 10 = skip any contract priced under 10c (which implies 90%+ certainty on one side)
MIN_COPY_PRICE_CENTS = int(os.getenv("MIN_COPY_PRICE_CENTS", "10"))

# --- Bot Behavior ---
# How often to poll markets (seconds)
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
# Set to True to disable real trades — only send alerts
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

# --- Logging ---
TRADE_LOG_FILE = os.getenv("TRADE_LOG_FILE", "whale_trades.csv")
# File to persist seen trade IDs across restarts (prevents duplicate alerts)
SEEN_TRADES_FILE = os.getenv("SEEN_TRADES_FILE", "seen_trades.json")

# --- Market Filter ---
# Comma-separated series tickers to monitor on Kalshi.
# These are queried directly via the API's series_ticker parameter.
# Daily high temps (4 cities):
#   KXHIGHNY (NYC), KXHIGHCHI (Chicago), KXHIGHMIA (Miami), KXHIGHAUS (Austin)
# Precipitation & storms:
#   KXRAIN (rainfall), KXSNOW (snowfall), KXWIND (wind)
# Broader weather:
#   KXTEMP (temperature), KXWEATH (general weather), KXHMONTHRANGE (monthly range)
WEATHER_SERIES_TICKERS = [
    s.strip() for s in
    os.getenv(
        "WEATHER_SERIES",
        "KXHIGHNY,KXHIGHCHI,KXHIGHMIA,KXHIGHAUS,"
        "KXTEMP,KXHMONTHRANGE,"
        "KXRAIN,KXSNOW,KXWIND,KXWEATH"
    ).split(",")
    if s.strip()
]

# --- Report Schedule (Central Time) ---
# Morning briefing: 8:00 AM Central
MORNING_REPORT_HOUR = int(os.getenv("MORNING_REPORT_HOUR", "8"))
MORNING_REPORT_MINUTE = int(os.getenv("MORNING_REPORT_MINUTE", "0"))
# Central Daylight Time = UTC-5 (March-November), CST = UTC-6
MORNING_REPORT_UTC_OFFSET = int(os.getenv("MORNING_REPORT_UTC_OFFSET", "-5"))

# Evening recap: 8:00 PM Central
EVENING_RECAP_HOUR = int(os.getenv("EVENING_RECAP_HOUR", "20"))
EVENING_RECAP_MINUTE = int(os.getenv("EVENING_RECAP_MINUTE", "0"))
