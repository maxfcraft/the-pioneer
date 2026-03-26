"""
Telegram bot — outbound alerts + inbound command handler.

Personality: Alfred Pennyworth — loyal, dry wit, protective, wise.

Outbound: Sends whale alerts, startup messages, errors, and hourly briefings.
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
    copy_amount = config.PAPER_COPY_AMOUNT_CENTS
    copy_count = max(1, copy_amount // alert.trade_price_cents)
    copy_cost_dollars = (copy_count * alert.trade_price_cents) / 100

    message = (
        f"Master Bruce, we have a whale.\n"
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
        f"Multiplier: {alert.multiplier}x average\n"
        f"Confidence: {alert.confidence_score}/100\n"
        f"\n"
        f"Paper Copy: {copy_count} contracts @ {alert.trade_price_cents}c = ${copy_cost_dollars:.2f}\n"
        f"Tracking this. Results at 8 PM.\n"
        f"{'='*30}\n"
        f"\n"
        f"Some men aren't looking for anything logical.\n"
        f"This one's betting big. I've matched accordingly."
    )

    return _send_message(message)


def send_startup_message(paper_mode: bool, market_count: int) -> bool:
    mode = "PAPER TRADING" if paper_mode else "LIVE TRADING"
    message = (
        f"Good evening, Master Bruce. The cave is online.\n"
        f"\n"
        f"{'='*30}\n"
        f"ALFRED WHALE DETECTION SYSTEM\n"
        f"{'='*30}\n"
        f"\n"
        f"Mode: {mode} (SNIPER)\n"
        f"Monitoring: {market_count} weather markets\n"
        f"Threshold: {config.WHALE_THRESHOLD_MULTIPLIER}x average\n"
        f"Min trade size: ${config.WHALE_MIN_DOLLAR_SIZE:.0f}\n"
        f"Price range: {config.MIN_COPY_PRICE_CENTS}c-{config.MAX_COPY_PRICE_CENTS}c (no penny bets, no near-certainties)\n"
        f"Paper copy: ${config.PAPER_COPY_AMOUNT_CENTS/100:.0f} per trade\n"
        f"Poll interval: {config.POLL_INTERVAL_SECONDS}s\n"
        f"\n"
        f"You'll hear from me:\n"
        f"  - Instantly on real whale detections ($50+ at 25x+, 10c-90c range)\n"
        f"  - Morning briefing at 7 AM\n"
        f"  - End-of-day recap at 8 PM (with $10 copy P&L)\n"
        f"\n"
        f"Commands: /status /today /recap /recap yesterday /balance /help\n"
        f"\n"
        f"I shall be watching the markets, Master Bruce.\n"
        f"Do try to get some sleep."
    )
    return _send_message(message)


def send_error_message(error: str) -> bool:
    message = (
        f"Master Bruce, I'm afraid we have a problem.\n"
        f"\n"
        f"{error}\n"
        f"\n"
        f"I'm working to resolve it. Do try not to worry."
    )
    return _send_message(message)


def send_trade_followup(trade, entry_price: int) -> bool:
    """Send the 1-hour follow-up report for a paper trade."""
    pnl_dollars = trade.pnl_cents / 100
    price_change = trade.exit_price_cents - entry_price
    direction = "UP" if price_change > 0 else "DOWN" if price_change < 0 else "FLAT"
    status = "SETTLED" if trade.resolved else "STILL OPEN"

    if trade.pnl_cents > 0:
        verdict = "The whale was right. This one would have printed."
    elif trade.pnl_cents < 0:
        verdict = "The whale got burned on this one. Sometimes even Gotham's finest get it wrong."
    else:
        verdict = "No movement yet. The market hasn't made up its mind."

    message = (
        f"Master Bruce, 1-hour check-in on {trade.codename}.\n"
        f"\n"
        f"{'='*30}\n"
        f"TRADE FOLLOW-UP — {trade.codename.upper()}\n"
        f"{'='*30}\n"
        f"\n"
        f"Market: {trade.market_title}\n"
        f"Ticker: {trade.market_ticker}\n"
        f"\n"
        f"Entry: {entry_price}c ({trade.side.upper()})\n"
        f"Now: {trade.exit_price_cents}c ({direction} {abs(price_change)}c)\n"
        f"Status: {status}\n"
        f"\n"
        f"Paper P&L: ${pnl_dollars:+.2f} ({trade.contract_count} contracts)\n"
        f"Whale was: {trade.whale_multiplier:.1f}x avg | Conf: {trade.confidence}\n"
        f"{'='*30}\n"
        f"\n"
        f"{verdict}"
    )
    return _send_message(message)


def send_near_miss_alert(near_miss: dict) -> bool:
    """Alert when a trade is big but didn't quite hit whale threshold."""
    pct_to_whale = (near_miss["multiplier"] / config.WHALE_THRESHOLD_MULTIPLIER) * 100
    message = (
        f"Master Bruce, something is stirring.\n"
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
        f"I've seen this pattern before. Watching closely."
    )
    return _send_message(message)


def send_volume_spike_alert(spike: VolumeSpikeAlert) -> bool:
    """Alert when a market suddenly gets way more trades than normal."""
    message = (
        f"Master Bruce, unusual activity.\n"
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
        f"The crowd is rushing in. When the masses move,\n"
        f"a whale is often not far behind."
    )
    return _send_message(message)


def send_hourly_briefing(stats: dict, near_misses: list, volume_spikes: list) -> bool:
    """Hourly Alfred-style check-in with market activity summary."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")

    lines = [
        f"Hourly briefing, Master Bruce — {now}.",
        "",
        f"{'='*30}",
        "MARKET BRIEFING",
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

    # Overall assessment — Alfred style
    lines.append("")
    if stats["whales"] > 0:
        lines.append("We caught one this hour, Master Bruce. Check the whale alerts above.")
    elif stats["near_misses"] >= 3:
        lines.append("Multiple near misses. The water is getting choppy. I'd keep an eye on this if I were you.")
    elif stats["volume_spikes"] > 0:
        lines.append("Volume is picking up. Where there's smoke, there's usually fire.")
    elif stats["trades_analyzed"] > 100:
        lines.append("Steady activity. No whales yet, but the markets are awake. Patience, Master Bruce.")
    elif stats["trades_analyzed"] > 0:
        lines.append("Quiet hour. Markets are moving slowly. I remain at my post.")
    else:
        lines.append("Very little activity this hour. Even the markets need rest occasionally.")

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
            reply = "Master Bruce, here's your current status.\n\n"
            reply += _activity_tracker.format_status_report()
            if _kalshi_client and _kalshi_client.authenticated:
                try:
                    bal = _kalshi_client.get_balance()
                    cents = bal.get("balance", 0)
                    reply += f"\nKalshi Balance: ${cents/100:.2f}\n"
                except Exception:
                    reply += "\nKalshi Balance: (could not fetch)\n"
            reply += "\nAll systems nominal. The cave is secure."
            return reply
        return "Master Bruce, the systems are running but I haven't collected any data yet. Give me a moment."

    elif cmd in ("/today", "today"):
        if _activity_tracker:
            return "Master Bruce, today's briefing.\n\n" + _activity_tracker.format_status_report()
        return "Master Bruce, no activity data for today yet. I've only just started."

    elif cmd in ("/yesterday", "yesterday"):
        if _activity_tracker:
            return "Master Bruce, yesterday's debrief.\n\n" + _activity_tracker.format_morning_report()
        return "Master Bruce, I'm afraid I don't have any data from yesterday."

    elif cmd in ("/recap", "recap"):
        if _paper_tracker:
            # Check latest prices before generating recap
            if _kalshi_client:
                _paper_tracker.check_outcomes(_kalshi_client)
            # Check if user wants yesterday's recap
            parts = text.strip().lower().split()
            if len(parts) > 1 and parts[1] == "yesterday":
                yesterday = _paper_tracker.get_yesterday_trades()
                if yesterday:
                    recap = _paper_tracker.format_recap(yesterday)
                    return f"Master Bruce, yesterday's paper trade recap.\n\n{recap}"
                return "No paper trades recorded yesterday, Master Bruce."
            today = _paper_tracker.get_today_trades()
            if today:
                recap = _paper_tracker.format_recap(today)
                return f"Master Bruce, your paper trade recap.\n\n{recap}"
            # Try recent trades if nothing today
            recent = _paper_tracker.get_recent_trades(days=7)
            if recent:
                recap = _paper_tracker.format_recap(recent)
                return f"No trades today, Master Bruce. Here's the last 7 days.\n\n{recap}"
            return "No paper trades recorded yet, Master Bruce. I'll track them when I detect whales."
        return "Master Bruce, the paper trade tracker isn't initialized yet."

    elif cmd in ("/balance", "balance"):
        if _kalshi_client:
            if not _kalshi_client.authenticated:
                return "Master Bruce, balance check requires a valid Kalshi API key. Currently running in public monitoring mode."
            try:
                bal = _kalshi_client.get_balance()
                cents = bal.get("balance", 0)
                return f"Master Bruce, your current Kalshi balance is ${cents/100:.2f}."
            except Exception as e:
                return f"I'm afraid I couldn't fetch your balance, Master Bruce. Error: {e}"
        return "Master Bruce, the Kalshi client isn't initialized yet."

    elif cmd in ("/datacheck", "datacheck"):
        if _whale_detector and _whale_detector.trade_history:
            lines = ["Master Bruce, live data health check.\n"]
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
                lines.append(f"\nWARNING: {zero_markets} markets have all-zero data")
                lines.append("Something is wrong with the data feed, Master Bruce.")
            else:
                lines.append("\nData flow: HEALTHY")
                lines.append("Everything is in order. The instruments are reading clearly.")

            return "\n".join(lines)
        return "No trade data in memory yet, Master Bruce. The system needs a few scan cycles to build up history."

    elif cmd in ("/help", "help"):
        return (
            "At your service, Master Bruce.\n"
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
            "  - Hourly briefing (7 AM - 8 PM Central)\n"
            "  - Morning briefing — 7 AM Central\n"
            "  - End-of-day recap — 8 PM Central\n"
            "\n"
            "Why do we fall, Master Bruce?\n"
            "So that we can learn to pick ourselves up."
        )

    else:
        return (
            f"I'm afraid I didn't understand that, Master Bruce — '{text}'.\n"
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
