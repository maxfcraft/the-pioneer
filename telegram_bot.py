"""
Telegram notification sender.

Sends formatted whale alert messages to your personal Telegram chat
via the Telegram Bot API.
"""

import requests
import config
from whale_detector import WhaleAlert


def send_whale_alert(alert: WhaleAlert, trade_placed: bool, paper_mode: bool,
                     balance_cents: int = 0) -> bool:
    """
    Send a formatted whale alert message to Telegram.

    Args:
        alert: The WhaleAlert object with all trade details
        trade_placed: Whether a copy-trade was actually placed
        paper_mode: Whether we're in paper trading mode
        balance_cents: Current portfolio balance in cents

    Returns:
        True if message sent successfully, False otherwise
    """
    mode_tag = "[PAPER]" if paper_mode else "[LIVE]"
    trade_status = "TRADE PLACED" if trade_placed else "ALERT ONLY"
    if paper_mode:
        trade_status = "PAPER MODE (no real trade)"

    whale_size_dollars = alert.trade_total_cents / 100
    balance_dollars = balance_cents / 100
    risk_pct = int(config.PORTFOLIO_RISK_FRACTION * 100)
    risk_dollars = balance_dollars * config.PORTFOLIO_RISK_FRACTION
    copy_count = max(1, int(risk_dollars * 100) // alert.trade_price_cents)
    copy_cost_dollars = (copy_count * alert.trade_price_cents) / 100

    message = (
        f"{'='*30}\n"
        f"WHALE DETECTED {mode_tag}\n"
        f"{'='*30}\n"
        f"\n"
        f"Market: {alert.market_title}\n"
        f"Ticker: {alert.market_ticker}\n"
        f"\n"
        f"Whale Trade: {alert.trade_count} contracts\n"
        f"Direction: {alert.trade_side.upper()}\n"
        f"Price: {alert.trade_price_cents}c per contract\n"
        f"Whale Total: ${whale_size_dollars:,.2f}\n"
        f"\n"
        f"Rolling Avg: {alert.rolling_average} contracts\n"
        f"Multiplier: {alert.multiplier}x average\n"
        f"Confidence: {alert.confidence_score}/100\n"
        f"\n"
        f"Your Balance: ${balance_dollars:,.2f}\n"
        f"Your Trade: {copy_count} contracts @ {alert.trade_price_cents}c = ${copy_cost_dollars:,.2f} ({risk_pct}% of balance)\n"
        f"Status: {trade_status}\n"
        f"{'='*30}"
    )

    return _send_message(message)


def send_startup_message(paper_mode: bool, market_count: int) -> bool:
    """Send a message when the bot starts up."""
    mode = "PAPER TRADING" if paper_mode else "LIVE TRADING"
    message = (
        f"Kalshi Whale Bot Started\n"
        f"Mode: {mode}\n"
        f"Monitoring: {market_count} weather markets\n"
        f"Threshold: {config.WHALE_THRESHOLD_MULTIPLIER}x average\n"
        f"Poll interval: {config.POLL_INTERVAL_SECONDS}s\n"
        f"Portfolio risk: {int(config.PORTFOLIO_RISK_FRACTION * 100)}% per trade"
    )
    return _send_message(message)


def send_error_message(error: str) -> bool:
    """Send an error notification."""
    message = f"[ERROR] Kalshi Whale Bot\n\n{error}"
    return _send_message(message)


def _send_message(text: str) -> bool:
    """Send a raw text message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[TELEGRAM ERROR] Failed to send message: {e}")
        return False
