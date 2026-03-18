import os
from dotenv import load_dotenv

load_dotenv()

# --- Kalshi API ---
KALSHI_API_KEY_ID = os.getenv("KALSHI_API_KEY_ID", "")
KALSHI_RSA_PRIVATE_KEY_PATH = os.getenv("KALSHI_RSA_PRIVATE_KEY_PATH", "")
KALSHI_BASE_URL = os.getenv("KALSHI_BASE_URL", "https://api.elections.kalshi.com/trade-api/v2")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Whale Detection ---
# A trade is a "whale" if its size is >= this multiplier times the rolling average
WHALE_THRESHOLD_MULTIPLIER = float(os.getenv("WHALE_THRESHOLD_MULTIPLIER", "10"))
# Number of recent trades used to calculate the rolling average
ROLLING_WINDOW_SIZE = int(os.getenv("ROLLING_WINDOW_SIZE", "100"))

# --- Trading ---
# What percentage of your portfolio balance to risk per whale trade (0.15 = 15%)
PORTFOLIO_RISK_FRACTION = float(os.getenv("PORTFOLIO_RISK_FRACTION", "0.15"))
# Minimum trade size in cents to place (avoids dust trades)
MIN_TRADE_SIZE_CENTS = int(os.getenv("MIN_TRADE_SIZE_CENTS", "100"))

# --- Bot Behavior ---
# How often to poll markets (seconds)
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
# Set to True to disable real trades — only send alerts
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

# --- Logging ---
TRADE_LOG_FILE = os.getenv("TRADE_LOG_FILE", "whale_trades.csv")

# --- Market Filter ---
# Only monitor markets whose ticker contains this string (case-insensitive)
# Examples: "WEATHER", "TEMP", "RAIN"
MARKET_FILTER = os.getenv("MARKET_FILTER", "WEATHER")
