"""
Kalshi Weather Market Whale Bot — Entry Point

Runs a continuous loop that:
1. Fetches all open weather markets from Kalshi
2. Pulls recent trades for each market
3. Runs whale detection on the trades
4. Sends Telegram alerts for any whales found
5. Optionally copies the trade (or skips in paper mode)
6. Logs everything to a CSV file
"""

import csv
import math
import os
import sys
import time
from datetime import datetime, timezone

import config
from kalshi_client import KalshiClient
from whale_detector import WhaleDetector, WhaleAlert
from telegram_bot import send_whale_alert, send_startup_message, send_error_message


def init_csv_log():
    """Create the CSV log file with headers if it doesn't exist."""
    if not os.path.exists(config.TRADE_LOG_FILE):
        with open(config.TRADE_LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "market_ticker",
                "market_title",
                "trade_count",
                "trade_side",
                "trade_price_cents",
                "trade_total_cents",
                "rolling_average",
                "multiplier",
                "confidence_score",
                "copy_trade_placed",
                "copy_trade_count",
                "paper_mode",
            ])


def log_whale(alert: WhaleAlert, trade_placed: bool, copy_count: int):
    """Append a whale detection to the CSV log."""
    with open(config.TRADE_LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            alert.market_ticker,
            alert.market_title,
            alert.trade_count,
            alert.trade_side,
            alert.trade_price_cents,
            alert.trade_total_cents,
            alert.rolling_average,
            alert.multiplier,
            alert.confidence_score,
            trade_placed,
            copy_count,
            config.PAPER_TRADING,
        ])


def copy_trade(client: KalshiClient, alert: WhaleAlert, balance_cents: int) -> tuple[bool, int, int]:
    """
    Copy a whale trade sized as a percentage of your portfolio balance.

    Returns:
        (success, contract_count, risk_cents) — whether the order went through,
        how many contracts, and total cost in cents
    """
    risk_cents = math.floor(balance_cents * config.PORTFOLIO_RISK_FRACTION)
    copy_count = max(1, risk_cents // alert.trade_price_cents)
    cost_cents = copy_count * alert.trade_price_cents

    if cost_cents < config.MIN_TRADE_SIZE_CENTS:
        print(f"  [SKIP] Copy trade too small: {cost_cents}c < {config.MIN_TRADE_SIZE_CENTS}c minimum")
        return False, 0, 0

    if config.PAPER_TRADING:
        print(f"  [PAPER] Would place: {copy_count} contracts {alert.trade_side.upper()} "
              f"@ {alert.trade_price_cents}c on {alert.market_ticker} "
              f"(${cost_cents/100:.2f} = {int(config.PORTFOLIO_RISK_FRACTION*100)}% of ${balance_cents/100:.2f} balance)")
        return False, copy_count, cost_cents

    try:
        result = client.place_order(
            ticker=alert.market_ticker,
            side=alert.trade_side,
            count=copy_count,
            price_cents=alert.trade_price_cents,
            order_type="limit",
        )
        order_id = result.get("order", {}).get("order_id", "unknown")
        print(f"  [TRADE] Order placed: {copy_count} contracts {alert.trade_side.upper()} "
              f"@ {alert.trade_price_cents}c — Order ID: {order_id} "
              f"(${cost_cents/100:.2f} = {int(config.PORTFOLIO_RISK_FRACTION*100)}% of balance)")
        return True, copy_count, cost_cents
    except Exception as e:
        error_msg = f"Failed to place copy trade on {alert.market_ticker}: {e}"
        print(f"  [ERROR] {error_msg}")
        send_error_message(error_msg)
        return False, copy_count, cost_cents


def run_scan(client: KalshiClient, detector: WhaleDetector):
    """Run one full scan cycle across all weather markets."""
    # Fetch balance once per scan cycle for position sizing
    try:
        balance_data = client.get_balance()
        balance_cents = balance_data.get("balance", 0)
        print(f"  Portfolio balance: ${balance_cents / 100:.2f}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch balance: {e}")
        balance_cents = 0

    try:
        markets = client.get_weather_markets()
    except Exception as e:
        print(f"[ERROR] Failed to fetch markets: {e}")
        return

    if not markets:
        print("[INFO] No weather markets found matching filter")
        return

    total_whales = 0

    for market in markets:
        ticker = market.get("ticker", "")
        title = market.get("title", ticker)

        try:
            trades_data = client.get_trades(ticker, limit=config.ROLLING_WINDOW_SIZE)
            trades = trades_data.get("trades", [])
        except Exception as e:
            print(f"  [ERROR] Failed to fetch trades for {ticker}: {e}")
            continue

        if not trades:
            continue

        alerts = detector.process_trades(ticker, trades, title)

        for alert in alerts:
            total_whales += 1
            print(f"\n  WHALE DETECTED in {alert.market_ticker}")
            print(f"    Size: {alert.trade_count} contracts ({alert.multiplier}x avg)")
            print(f"    Side: {alert.trade_side.upper()} @ {alert.trade_price_cents}c")
            print(f"    Confidence: {alert.confidence_score}/100")

            trade_placed, copy_count, cost_cents = copy_trade(client, alert, balance_cents)
            send_whale_alert(alert, trade_placed, config.PAPER_TRADING, balance_cents)
            log_whale(alert, trade_placed, copy_count)

    if total_whales == 0:
        print("  No whales this cycle")


def main():
    """Main entry point — initialize and run the bot loop."""
    print("=" * 50)
    print("  KALSHI WEATHER WHALE BOT")
    print(f"  Mode: {'PAPER TRADING' if config.PAPER_TRADING else 'LIVE TRADING'}")
    print(f"  Threshold: {config.WHALE_THRESHOLD_MULTIPLIER}x average")
    print(f"  Portfolio risk: {int(config.PORTFOLIO_RISK_FRACTION * 100)}% per trade")
    print(f"  Poll interval: {config.POLL_INTERVAL_SECONDS}s")
    print(f"  Market filter: {config.MARKET_FILTER}")
    print("=" * 50)

    # Validate required config
    missing = []
    if not config.KALSHI_API_KEY_ID:
        missing.append("KALSHI_API_KEY_ID")
    if not config.KALSHI_RSA_PRIVATE_KEY_PATH:
        missing.append("KALSHI_RSA_PRIVATE_KEY_PATH")
    if not config.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not config.TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        print(f"\n[FATAL] Missing required config: {', '.join(missing)}")
        print("Fill in your .env file and try again.")
        sys.exit(1)

    if not os.path.exists(config.KALSHI_RSA_PRIVATE_KEY_PATH):
        print(f"\n[FATAL] RSA private key file not found: {config.KALSHI_RSA_PRIVATE_KEY_PATH}")
        print("Save your Kalshi private key to this path and try again.")
        sys.exit(1)

    # Initialize
    print("\n[INIT] Connecting to Kalshi API...")
    client = KalshiClient()
    detector = WhaleDetector()
    init_csv_log()

    # Test connection by fetching markets
    try:
        markets = client.get_weather_markets()
        market_count = len(markets)
        print(f"[INIT] Found {market_count} weather markets")
    except Exception as e:
        print(f"[FATAL] Failed to connect to Kalshi API: {e}")
        sys.exit(1)

    # Send startup Telegram message
    send_startup_message(config.PAPER_TRADING, market_count)
    print("[INIT] Startup message sent to Telegram")
    print("\n[RUNNING] Bot is now monitoring. Press Ctrl+C to stop.\n")

    # Main loop
    cycle = 0
    while True:
        cycle += 1
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(f"[Cycle {cycle}] {timestamp} — Scanning {config.MARKET_FILTER} markets...")

        try:
            run_scan(client, detector)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[ERROR] Scan cycle failed: {e}")
            send_error_message(f"Scan cycle {cycle} failed: {e}")

        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Bot stopped by user.")
