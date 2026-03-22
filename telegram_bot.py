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
from whale_detector import WhaleAlert, VolumeSpikeAlert


# Will be set by main.py after ActivityTracker is created
_activity_tracker = None
_kalshi_client = None
_paper_tracker = None
_whale_detector = None


def set_activity_tracker(tracker):
    global _activity_tracker
    _activity_tracker = tracker


def set_kalshi_client(client):
    global _kalshi_client
    _kalshi_client = client


def set_paper_tracker(tracker):
    global _paper_tracker
    _paper_tracker = tracker


def set_whale_detector(detector):
    global _whale_detector
    _whale_detector = detector


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
        f"I'm at your service. You'll hear from me:\n"
        f"  - Instantly on whale detections\n"
        f"  - Instantly on near misses (7x+ avg)\n"
        f"  - Instantly on volume spikes (3x+ normal)\n"
        f"  - Hourly briefings with market summary\n"
        f"  - Morning briefing at 7 AM\n"
        f"  - End-of-day recap at 8 PM\n"
        f"\n"
        f"Commands: /status /today /recap /balance /datacheck /help\n"
        f"\n"
        f"Standing by, sir. I'll keep you posted."
    )
    return _send_message(message)


def send_error_message(error: str) -> bool:
    message = f"Sir, we have a problem.\n\n{error}\n\nI'm working to resolve it. Stand by."
    return _send_message(message)


def send_near_miss_alert(near_miss: dict) -> bool:
    """Alert when a trade is big but didn't quite hit whale threshold."""
    pct_to_whale = (near_miss["multiplier"] / config.WHALE_THRESHOLD_MULTIPLIER) * 100
    message = (
        f"Sir, activity heating up.\n"
        f"\n"
        f"{'='*30}\n"
        f"NEAR MISS DETECTED\n"
        f"{'='*30}\n"
        f"\n"
        f"Market: {near_miss['title']}\n"
        f"Ticker: {near_miss['ticker']}\n"
        f"\n"
        f"Trade size: {near_miss['count']} contracts\n"
        f"That's {near_miss['multiplier']:.1f}x the average\n"
        f"({pct_to_whale:.0f}% of whale threshold)\n"
        f"\n"
        f"Not a whale yet, but someone is positioning.\n"
        f"I'm watching this market closely, sir."
    )
    return _send_message(message)


def send_volume_spike_alert(spike: VolumeSpikeAlert) -> bool:
    """Alert when a market suddenly gets way more trades than normal."""
    message = (
        f"Sir, unusual activity detected.\n"
        f"\n"
        f"{'='*30}\n"
        f"VOLUME SPIKE\n"
        f"{'='*30}\n"
        f"\n"
        f"Market: {spike.market_title}\n"
        f"Ticker: {spike.market_ticker}\n"
        f"\n"
        f"New trades this scan: {spike.new_trade_count}\n"
        f"Normal avg per scan: {spike.avg_trades_per_scan}\n"
        f"Spike: {spike.spike_multiplier}x normal volume\n"
        f"\n"
        f"The crowd is rushing into this market.\n"
        f"Could precede a whale. Monitoring, sir."
    )
    return _send_message(message)


def send_hourly_briefing(stats: dict, near_misses: list, volume_spikes: list) -> bool:
    """Hourly Jarvis-style check-in with market activity summary."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")

    lines = [
        f"Sir, hourly briefing — {now}.",
        "",
        f"{'='*30}",
        "HOURLY MARKET BRIEFING",
        f"{'='*30}",
        "",
        f"Trades analyzed: {stats['trades_analyzed']}",
        f"Markets scanned: {stats['markets_scanned']}",
        f"Whales detected: {stats['whales']}",
        f"Near misses: {stats['near_misses']}",
        f"Volume spikes: {stats['volume_spikes']}",
    ]

    # Largest trade
    lt = stats["largest_trade"]
    if lt["count"] > 0:
        lines.append(f"\nBiggest trade: {lt['count']} contracts")
        lines.append(f"  Market: {lt['title']}")

    # Hottest market
    hm = stats["hottest_market"]
    if hm["new_trades"] > 0:
        lines.append(f"\nHottest market: {hm['title']}")
        lines.append(f"  {hm['new_trades']} new trades this hour")

    # Near misses
    if near_misses:
        lines.append(f"\nNearest misses:")
        # Show up to 3 closest to whale threshold
        sorted_nm = sorted(near_misses, key=lambda x: x["multiplier"], reverse=True)
        for nm in sorted_nm[:3]:
            pct = (nm["multiplier"] / config.WHALE_THRESHOLD_MULTIPLIER) * 100
            lines.append(f"  {nm['title']}")
            lines.append(f"    {nm['count']} contracts ({nm['multiplier']:.1f}x avg, {pct:.0f}% to whale)")

    # Volume spikes
    if volume_spikes:
        lines.append(f"\nVolume spikes:")
        for vs in volume_spikes[:3]:
            lines.append(f"  {vs.market_title}")
            lines.append(f"    {vs.new_trade_count} trades ({vs.spike_multiplier}x normal)")

    # Overall assessment
    lines.append("")
    if stats["whales"] > 0:
        lines.append("Action taken this hour. Check whale alerts above for details.")
    elif stats["near_misses"] >= 3:
        lines.append("Multiple near misses, sir. Markets are active. A whale could surface soon.")
    elif stats["volume_spikes"] > 0:
        lines.append("Volume picking up in some markets. I'm on it, sir.")
    elif stats["trades_analyzed"] > 0:
        lines.append("Markets are quiet but I'm watching every trade. Standing by, sir.")
    else:
        lines.append("Very low activity this hour. Markets may be between sessions, sir.")

    return _send_message("\n".join(lines))


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
            if _kalshi_client and _kalshi_client.authenticated:
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

    elif cmd in ("/recap", "recap"):
        if _paper_tracker:
            # Check latest prices before generating recap
            if _kalshi_client:
                _paper_tracker.check_outcomes(_kalshi_client)
            today = _paper_tracker.get_today_trades()
            if today:
                recap = _paper_tracker.format_recap(today)
                return f"Sir, here's your paper trade recap.\n\n{recap}"
            # Try recent trades if nothing today
            recent = _paper_tracker.get_recent_trades(days=7)
            if recent:
                recap = _paper_tracker.format_recap(recent)
                return f"Sir, no trades today. Here's the last 7 days.\n\n{recap}"
            return "Sir, no paper trades recorded yet. I'll track them when I detect whales."
        return "Sir, the paper trade tracker isn't initialized yet."

    elif cmd in ("/balance", "balance"):
        if _kalshi_client:
            if not _kalshi_client.authenticated:
                return "Sir, balance check requires a valid Kalshi API key. Currently running in public monitoring mode."
            try:
                bal = _kalshi_client.get_balance()
                cents = bal.get("balance", 0)
                return f"Sir, your current Kalshi balance is ${cents/100:.2f}."
            except Exception as e:
                return f"Sir, I wasn't able to fetch your balance. Error: {e}"
        return "Sir, the Kalshi client isn't initialized yet."

    elif cmd in ("/datacheck", "datacheck"):
        if _whale_detector and _whale_detector.trade_history:
            lines = ["Sir, here's the live data health check.\n"]
            lines.append(f"Markets with data: {len(_whale_detector.trade_history)}")
            total_entries = sum(len(h) for h in _whale_detector.trade_history.values())
            lines.append(f"Total trade entries in memory: {total_entries}\n")

            # Show top 5 markets by average trade size
            market_avgs = []
            for ticker, history in _whale_detector.trade_history.items():
                if history:
                    avg = sum(history) / len(history)
                    max_trade = max(history)
                    market_avgs.append((ticker, avg, max_trade, len(history)))
            market_avgs.sort(key=lambda x: x[1], reverse=True)

            lines.append("Top 5 markets by avg trade size:")
            for ticker, avg, max_t, count in market_avgs[:5]:
                threshold = avg * config.WHALE_THRESHOLD_MULTIPLIER
                lines.append(f"  {ticker[-20:]}")
                lines.append(f"    Avg: {avg:.1f} | Max: {max_t} | Whale threshold: {threshold:.0f}")
                lines.append(f"    History: {count} trades")

            # Near miss summary
            nm_count = len(_whale_detector.last_near_misses)
            lines.append(f"\nNear misses (5-10x): {nm_count}")
            if _whale_detector.last_near_misses:
                for nm in _whale_detector.last_near_misses[-3:]:
                    lines.append(f"  {nm['ticker'][-20:]}: {nm['count']} contracts ({nm['multiplier']:.1f}x)")

            # Data flowing check
            zero_markets = sum(1 for h in _whale_detector.trade_history.values() if h and max(h) == 0)
            if zero_markets > 0:
                lines.append(f"\nWARNING: {zero_markets} markets have all-zero data (API bug)")
            else:
                lines.append("\nData flow: HEALTHY - real trade sizes detected")

            return "\n".join(lines)
        return "Sir, no trade data in memory yet. The detector needs a few scan cycles to build up history."

    elif cmd in ("/help", "help"):
        return (
            "At your service, sir. Here's what I can do:\n"
            "\n"
            "  /status     - Quick status + today's stats\n"
            "  /today      - Full report for today so far\n"
            "  /yesterday  - Yesterday's summary report\n"
            "  /recap      - Paper trade P&L recap\n"
            "  /balance    - Your Kalshi balance\n"
            "  /datacheck  - Live data health + trade sizes\n"
            "  /help       - This message\n"
            "\n"
            "Automatic alerts:\n"
            "  - Whale detections (10x+ avg) — instant\n"
            "  - Near misses (7x+ avg) — instant\n"
            "  - Volume spikes (3x+ normal) — instant\n"
            "  - Hourly market briefing — every 60 min\n"
            "  - Morning briefing — 7 AM Central\n"
            "  - End-of-day recap — 8 PM Central\n"
            "\n"
            "I'm always watching, sir."
        )

    else:
        return (
            f"Sir, I didn't quite catch that — '{text}'.\n"
            f"Try /status, /today, /recap, /balance, /datacheck, or /help."
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
