"""
Telegram bot — outbound alerts + inbound command handler.

Outbound: Sends whale alerts, startup messages, errors, and morning reports.
Inbound:  Listens for your commands via long-polling and replies with bot status.

Supported commands:
  /status   — Current bot status + today's stats
  /today    — Full report for today so far
  /yesterday — Full report for yesterday
  /help     — List available commands
"""

import threading
import time
import requests
import config
from whale_detector import WhaleAlert


# Will be set by main.py after ActivityTracker is created
_activity_tracker = None
_kalshi_client = None


def set_activity_tracker(tracker):
    global _activity_tracker
    _activity_tracker = tracker


def set_kalshi_client(client):
    global _kalshi_client
    _kalshi_client = client


# ── Outbound messages ────────────────────────────────────────────

def send_whale_alert(alert: WhaleAlert, trade_placed: bool, paper_mode: bool,
                     balance_cents: int = 0) -> bool:
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
        f"Sir, I've detected a whale.\n"
        f"\n"
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
        f"Copy Trade: {copy_count} contracts @ {alert.trade_price_cents}c = ${copy_cost_dollars:,.2f} ({risk_pct}% of balance)\n"
        f"Status: {trade_status}\n"
        f"{'='*30}\n"
        f"\n"
        f"Shall I continue monitoring, sir?"
    )

    return _send_message(message)


def send_startup_message(paper_mode: bool, market_count: int) -> bool:
    mode = "PAPER TRADING" if paper_mode else "LIVE TRADING"
    message = (
        f"Good day, sir. All systems are online.\n"
        f"\n"
        f"{'='*30}\n"
        f"JARVIS WHALE DETECTION SYSTEM\n"
        f"{'='*30}\n"
        f"\n"
        f"Mode: {mode}\n"
        f"Monitoring: {market_count} weather markets\n"
        f"Threshold: {config.WHALE_THRESHOLD_MULTIPLIER}x average\n"
        f"Poll interval: {config.POLL_INTERVAL_SECONDS}s\n"
        f"Portfolio risk: {int(config.PORTFOLIO_RISK_FRACTION * 100)}% per trade\n"
        f"\n"
        f"I'm at your service. Available commands:\n"
        f"  /status  - Quick status check\n"
        f"  /today   - Today's full report\n"
        f"  /yesterday - Yesterday's summary\n"
        f"  /balance - Your Kalshi balance\n"
        f"  /help    - All commands\n"
        f"\n"
        f"I'll notify you the moment I spot a whale, sir."
    )
    return _send_message(message)


def send_error_message(error: str) -> bool:
    message = f"Sir, we have a problem.\n\n{error}\n\nI'm working to resolve it. Stand by."
    return _send_message(message)


def send_morning_report(report_text: str) -> bool:
    return _send_message(report_text)


def _send_message(text: str) -> bool:
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


# ── Inbound command handler (runs in background thread) ──────────

def _handle_command(text: str) -> str:
    """Process a user command and return the reply text."""
    cmd = text.strip().lower().split()[0] if text.strip() else ""

    if cmd in ("/status", "status", "whats the update", "update"):
        if _activity_tracker:
            reply = "Sir, here's your current status.\n\n"
            reply += _activity_tracker.format_status_report()
            if _kalshi_client:
                try:
                    bal = _kalshi_client.get_balance()
                    cents = bal.get("balance", 0)
                    reply += f"\nKalshi Balance: ${cents/100:.2f}\n"
                except Exception:
                    reply += "\nKalshi Balance: (could not fetch)\n"
            reply += "\nAll systems nominal, sir."
            return reply
        return "Sir, the bot is running but I haven't collected any data yet. Stand by."

    elif cmd in ("/today", "today"):
        if _activity_tracker:
            return "Sir, here's today's full briefing.\n\n" + _activity_tracker.format_status_report()
        return "Sir, no activity data for today yet. I've just started up."

    elif cmd in ("/yesterday", "yesterday"):
        if _activity_tracker:
            return "Sir, here's yesterday's debrief.\n\n" + _activity_tracker.format_morning_report()
        return "Sir, I don't have any data from yesterday."

    elif cmd in ("/balance", "balance"):
        if _kalshi_client:
            try:
                bal = _kalshi_client.get_balance()
                cents = bal.get("balance", 0)
                return f"Sir, your current Kalshi balance is ${cents/100:.2f}."
            except Exception as e:
                return f"Sir, I wasn't able to fetch your balance. Error: {e}"
        return "Sir, the Kalshi client isn't initialized yet."

    elif cmd in ("/help", "help"):
        return (
            "At your service, sir. Here's what I can do:\n"
            "\n"
            "  /status     - Quick status + today's stats + balance\n"
            "  /today      - Full report for today so far\n"
            "  /yesterday  - Yesterday's summary report\n"
            "  /balance    - Your current Kalshi balance\n"
            "  /help       - This message\n"
            "\n"
            "You can also just say things like:\n"
            "  'whats the update'\n"
            "  'status'\n"
            "  'balance'\n"
            "\n"
            "I'm always listening, sir."
        )

    else:
        return (
            f"Sir, I didn't quite catch that — '{text}'.\n"
            f"Try /status, /today, /yesterday, /balance, or /help."
        )


def _poll_for_messages():
    """Long-poll the Telegram API for incoming messages (runs in daemon thread)."""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates"
    offset = 0

    print("[TELEGRAM] Command listener started")

    while True:
        try:
            params = {
                "offset": offset,
                "timeout": 30,  # long-poll: wait up to 30s for new messages
                "allowed_updates": ["message"],
            }
            resp = requests.get(url, params=params, timeout=35)
            resp.raise_for_status()
            data = resp.json()

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "")

                # Only respond to messages from our configured chat
                if chat_id != config.TELEGRAM_CHAT_ID:
                    continue

                if not text:
                    continue

                print(f"[TELEGRAM] Received command: {text}")
                reply = _handle_command(text)
                _send_message(reply)

        except requests.exceptions.Timeout:
            continue  # Normal — long-poll timeout just means no new messages
        except Exception as e:
            print(f"[TELEGRAM POLL ERROR] {e}")
            time.sleep(5)  # back off on errors


def start_command_listener():
    """Start the background thread that listens for Telegram commands."""
    thread = threading.Thread(target=_poll_for_messages, daemon=True)
    thread.start()
    return thread
