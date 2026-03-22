"""
Kalshi Weather Market Whale Bot — Entry Point

Runs a continuous loop that:
1. Fetches all open weather markets from Kalshi
2. Pulls recent trades for each market
3. Runs whale detection on the trades
4. Sends Telegram alerts for any whales found
5. Optionally copies the trade (or skips in paper mode)
6. Logs everything to a CSV file
7. Tracks daily activity for status reports
8. Listens for Telegram commands (/status, /today, etc.)
9. Sends automated morning report at 7 AM
"""

import csv
import math
import os
import sys
import time
import threading
from datetime import datetime, timezone, timedelta

import config
from kalshi_client import KalshiClient
from whale_detector import WhaleDetector, WhaleAlert
from activity_tracker import ActivityTracker
from paper_tracker import PaperTradeTracker
from telegram_bot import (
    send_whale_alert, send_startup_message, send_error_message,
    send_near_miss_alert, send_volume_spike_alert, send_hourly_briefing,
    send_trade_followup,
    set_activity_tracker, set_kalshi_client, set_paper_tracker, set_whale_detector,
    start_command_listener, _send_message,
)
from morning_report import start_morning_report_scheduler


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


def _trade_followup(client: KalshiClient, paper_tracker: PaperTradeTracker, trade_index: int, entry_price: int):
    """Called 1 hour after a paper trade to check how it's doing."""
    try:
        trade = paper_tracker.trades[trade_index]
        updated = paper_tracker.check_single_trade(trade, client)
        if updated:
            send_trade_followup(updated, entry_price)
            print(f"[FOLLOWUP] Sent 1-hour check for {trade.codename}: {trade.market_ticker}")
        else:
            print(f"[FOLLOWUP] Could not check {trade.codename}")
    except Exception as e:
        print(f"[FOLLOWUP ERROR] {e}")


def schedule_trade_followup(client: KalshiClient, paper_tracker: PaperTradeTracker,
                            trade_index: int, entry_price: int):
    """Schedule a 1-hour follow-up check for a paper trade."""
    timer = threading.Timer(
        3600,  # 1 hour
        _trade_followup,
        args=(client, paper_tracker, trade_index, entry_price),
    )
    timer.daemon = True
    timer.start()


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


def run_scan(client: KalshiClient, detector: WhaleDetector, tracker: ActivityTracker,
             paper_tracker: PaperTradeTracker = None):
    """Run one full scan cycle across all weather markets."""
    # Fetch balance once per scan cycle for position sizing (skip if no auth)
    balance_cents = 0
    if client.authenticated:
        try:
            balance_data = client.get_balance()
            balance_cents = balance_data.get("balance", 0)
        except Exception:
            pass

    try:
        markets = client.get_weather_markets()
    except Exception as e:
        print(f"[ERROR] Failed to fetch markets: {e}")
        tracker.record_error()
        return

    if not markets:
        print("[INFO] No weather markets found matching filter")
        return

    total_whales = 0
    total_trades = 0

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

        total_trades += len(trades)
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

            # Record paper trade for outcome tracking + schedule 1hr follow-up
            if config.PAPER_TRADING and paper_tracker and copy_count > 0:
                recorded_trade = paper_tracker.record_trade(
                    ticker=alert.market_ticker,
                    title=alert.market_title,
                    side=alert.trade_side,
                    price_cents=alert.trade_price_cents,
                    count=copy_count,
                    multiplier=alert.multiplier,
                    confidence=alert.confidence_score,
                )
                # Tell them the codename
                _send_message(
                    f"This trade is designated {recorded_trade.codename}.\n"
                    f"I'll check back in 1 hour with a status report."
                )
                # Schedule the 1-hour follow-up
                trade_idx = len(paper_tracker.trades) - 1
                schedule_trade_followup(client, paper_tracker, trade_idx, alert.trade_price_cents)
                print(f"  [FOLLOWUP] Scheduled 1hr check for {recorded_trade.codename}")

            # Track in activity log
            tracker.record_whale(
                ticker=alert.market_ticker,
                title=alert.market_title,
                count=alert.trade_count,
                side=alert.trade_side,
                price_cents=alert.trade_price_cents,
                multiplier=alert.multiplier,
                confidence=alert.confidence_score,
                trade_placed=trade_placed,
                paper=config.PAPER_TRADING,
            )

    # Track near-miss data (log only — no Telegram spam)
    near_miss_count = len(detector.last_near_misses)
    for nm in detector.last_near_misses:
        tracker.record_near_miss(
            ticker=nm["ticker"], title=nm["title"], count=nm["count"],
            rolling_avg=nm["rolling_avg"], multiplier=nm["multiplier"],
        )
        if nm["multiplier"] >= config.WHALE_THRESHOLD_MULTIPLIER * 0.7:
            print(f"  NEAR MISS (logged): {nm['ticker']} — {nm['count']} contracts ({nm['multiplier']:.1f}x avg)")
    detector.last_near_misses.clear()

    # Track volume spikes (log only — no Telegram spam)
    for spike in detector.last_volume_spikes:
        print(f"  VOLUME SPIKE (logged): {spike.market_ticker} — {spike.new_trade_count} trades ({spike.spike_multiplier}x normal)")
    detector.last_volume_spikes.clear()

    # Update hourly market count
    detector.hourly_stats["markets_scanned"] = len(markets)

    # Track cycle in activity log
    tracker.record_cycle(markets_scanned=len(markets), trades_analyzed=total_trades)

    # Diagnostic: show real data is flowing through the detector
    sample_avgs = []
    for t, history in list(detector.trade_history.items())[:3]:
        if history:
            avg = sum(history) / len(history)
            sample_avgs.append(f"{t[-12:]}: avg={avg:.1f} ({len(history)} trades)")
    if sample_avgs:
        print(f"  Data check: {total_trades} trades | {near_miss_count} near-misses | {', '.join(sample_avgs)}")
    else:
        print(f"  Data check: {total_trades} trades analyzed")

    if total_whales == 0:
        print("  No whales this cycle")


def _city_from_ticker(ticker: str) -> str:
    """Extract a readable city name from a Kalshi weather ticker."""
    city_map = {
        "KXHIGHNY": "NYC",
        "KXHIGHCHI": "Chicago",
        "KXHIGHMIA": "Miami",
        "KXHIGHAUS": "Austin",
    }
    for prefix, name in city_map.items():
        if ticker.startswith(prefix):
            return name
    return ticker.split("-")[0].replace("KX", "")


def _build_scoreboard(trades: list) -> str:
    """Build a 7-day running scoreboard from paper trades."""
    total_pnl = sum(t.pnl_cents for t in trades)
    total_cost = sum(t.cost_cents for t in trades) or 1
    winners = [t for t in trades if t.pnl_cents > 0]
    losers = [t for t in trades if t.pnl_cents < 0]
    settled = [t for t in trades if t.resolved]
    open_trades = [t for t in trades if not t.resolved]

    win_rate = (len(winners) / len(settled) * 100) if settled else 0
    roi = (total_pnl / total_cost) * 100

    lines = [
        f"{'='*30}",
        f"7-DAY SCOREBOARD",
        f"{'='*30}",
        f"",
        f"Total trades: {len(trades)} ({len(settled)} settled, {len(open_trades)} open)",
        f"Record: {len(winners)}W / {len(losers)}L",
        f"Win rate: {win_rate:.0f}%",
        f"Net P&L: ${total_pnl/100:+.2f} ({roi:+.1f}% ROI)",
    ]

    # Best and worst trade
    if settled:
        best = max(settled, key=lambda t: t.pnl_cents)
        worst = min(settled, key=lambda t: t.pnl_cents)
        lines.append(f"")
        lines.append(f"Best trade: ${best.pnl_cents/100:+.2f} — {_city_from_ticker(best.market_ticker)}")
        lines.append(f"  {best.market_title}")
        lines.append(f"Worst trade: ${worst.pnl_cents/100:+.2f} — {_city_from_ticker(worst.market_ticker)}")
        lines.append(f"  {worst.market_title}")

    # City P&L breakdown
    city_pnl: dict[str, int] = {}
    city_count: dict[str, int] = {}
    for t in trades:
        city = _city_from_ticker(t.market_ticker)
        city_pnl[city] = city_pnl.get(city, 0) + t.pnl_cents
        city_count[city] = city_count.get(city, 0) + 1

    if city_pnl:
        lines.append(f"")
        lines.append(f"P&L by City:")
        for city in sorted(city_pnl, key=city_pnl.get, reverse=True):
            lines.append(f"  {city}: ${city_pnl[city]/100:+.2f} ({city_count[city]} trades)")

    # Confidence analysis
    high_conf = [t for t in settled if t.confidence >= 60]
    low_conf = [t for t in settled if t.confidence < 60]
    if high_conf and low_conf:
        hc_wins = sum(1 for t in high_conf if t.pnl_cents > 0)
        lc_wins = sum(1 for t in low_conf if t.pnl_cents > 0)
        hc_rate = (hc_wins / len(high_conf) * 100) if high_conf else 0
        lc_rate = (lc_wins / len(low_conf) * 100) if low_conf else 0
        lines.append(f"")
        lines.append(f"Confidence Breakdown:")
        lines.append(f"  High conf (60+): {hc_rate:.0f}% win rate ({len(high_conf)} trades)")
        lines.append(f"  Low conf (<60): {lc_rate:.0f}% win rate ({len(low_conf)} trades)")

    lines.append(f"{'='*30}")
    return "\n".join(lines)


def _eod_recap_loop(client: KalshiClient, paper_tracker: PaperTradeTracker):
    """Background thread: sends end-of-day paper trade recap at 8 PM Central."""
    recap_hour = config.EVENING_RECAP_HOUR  # 20 = 8 PM
    utc_offset = config.MORNING_REPORT_UTC_OFFSET  # -5 for CDT
    recap_utc_hour = (recap_hour - utc_offset) % 24

    print(f"[EOD RECAP] Scheduler started — recaps at {recap_hour % 12 or 12}:00 PM (UTC{utc_offset:+d})")

    while True:
        now = datetime.now(timezone.utc)
        target = now.replace(hour=recap_utc_hour, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        wait_secs = (target - datetime.now(timezone.utc)).total_seconds()
        print(f"[EOD RECAP] Next recap at {target.strftime('%Y-%m-%d %H:%M UTC')} "
              f"({wait_secs/3600:.1f}h from now)")

        while True:
            remaining = (target - datetime.now(timezone.utc)).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(remaining, 60))

        # Check outcomes for today's paper trades + build smart recap
        try:
            paper_tracker.check_outcomes(client)
            today_trades = paper_tracker.get_today_trades()
            recent_trades = paper_tracker.get_recent_trades(days=7)

            if today_trades:
                recap = paper_tracker.format_recap(today_trades)

                # Add 7-day running scoreboard
                if len(recent_trades) > len(today_trades):
                    scoreboard = _build_scoreboard(recent_trades)
                    recap += f"\n{scoreboard}"

                msg = f"Good evening, Master Bruce.\n\n{recap}"
                _send_message(msg)
                print(f"[EOD RECAP] Sent recap for {len(today_trades)} paper trades")
            else:
                # Even on quiet days, show the running scoreboard if we have data
                if recent_trades:
                    scoreboard = _build_scoreboard(recent_trades)
                    msg = (
                        f"Good evening, Master Bruce. No whales today.\n\n"
                        f"But here's where we stand this week:\n\n{scoreboard}"
                    )
                else:
                    msg = (
                        "Good evening, Master Bruce. No whale trades this week. "
                        "The markets have been quiet. I remain at my post."
                    )
                _send_message(msg)
                print("[EOD RECAP] No trades today, sent scoreboard")
        except Exception as e:
            print(f"[EOD RECAP ERROR] {e}")

        time.sleep(61)  # avoid double-send


def start_eod_recap_scheduler(client: KalshiClient, paper_tracker: PaperTradeTracker):
    """Start the background thread for end-of-day paper trade recaps."""
    thread = threading.Thread(target=_eod_recap_loop, args=(client, paper_tracker), daemon=True)
    thread.start()
    return thread


def _hourly_briefing_loop(detector):
    """Background thread: sends hourly Alfred briefing to Telegram (quiet 8PM-7AM Central)."""
    utc_offset = config.MORNING_REPORT_UTC_OFFSET  # -5 for CDT
    print("[HOURLY] Briefing scheduler started — updates every 60 min (quiet 8PM-7AM Central)")

    while True:
        time.sleep(3600)  # Wait one hour

        # Check if we're in quiet hours (8 PM - 7 AM Central)
        now_utc = datetime.now(timezone.utc)
        central_hour = (now_utc.hour + utc_offset) % 24
        if central_hour >= 20 or central_hour < 7:
            # Still reset stats so the next active-hour briefing starts fresh
            detector.reset_hourly_stats()
            print(f"[HOURLY] Quiet hours ({central_hour}:00 Central) — skipping briefing")
            continue

        try:
            stats = detector.hourly_stats.copy()
            near_misses = list(detector.hourly_near_misses)
            volume_spikes = list(detector.last_volume_spikes)

            send_hourly_briefing(stats, near_misses, volume_spikes)
            print(f"[HOURLY] Briefing sent — {stats['trades_analyzed']} trades, "
                  f"{stats['whales']} whales, {stats['near_misses']} near misses")

            # Reset accumulators for next hour
            detector.reset_hourly_stats()
        except Exception as e:
            print(f"[HOURLY ERROR] {e}")


def start_hourly_briefing_scheduler(detector):
    """Start the background thread for hourly Telegram briefings."""
    thread = threading.Thread(target=_hourly_briefing_loop, args=(detector,), daemon=True)
    thread.start()
    return thread


def main():
    """Main entry point — initialize and run the bot loop."""
    print("=" * 50)
    print("  ALFRED — KALSHI WHALE DETECTION SYSTEM")
    print(f"  Mode: {'PAPER TRADING' if config.PAPER_TRADING else 'LIVE TRADING'}")
    print(f"  Threshold: {config.WHALE_THRESHOLD_MULTIPLIER}x average")
    print(f"  Portfolio risk: {int(config.PORTFOLIO_RISK_FRACTION * 100)}% per trade")
    print(f"  Poll interval: {config.POLL_INTERVAL_SECONDS}s")
    print(f"  Weather series: {', '.join(config.WEATHER_SERIES_TICKERS)}")
    print("=" * 50)

    # Validate required config — only Telegram is mandatory
    missing = []
    if not config.TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not config.TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        print(f"\n[FATAL] Missing required config: {', '.join(missing)}")
        print("Fill in your .env file and try again.")
        sys.exit(1)

    # Initialize
    print("\n[INIT] Connecting to Kalshi API...")
    client = KalshiClient()
    detector = WhaleDetector()
    tracker = ActivityTracker()
    init_csv_log()

    # Wire up Telegram command handler with tracker and client
    set_activity_tracker(tracker)
    set_kalshi_client(client)
    set_whale_detector(detector)

    if client.authenticated:
        try:
            bal = client.get_balance()
            print(f"[INIT] Authenticated — Balance: ${bal.get('balance', 0) / 100:.2f}")
        except Exception as e:
            print(f"[WARNING] Auth failed: {e}")
            print("[INIT] Continuing in public-only mode (whale alerts only, no copy trading)")
            client.authenticated = False
    else:
        print("[INIT] No valid API key — running in public-only mode (whale alerts only)")

    # Fetch weather markets to verify API connection works
    print("[INIT] Discovering weather markets (this may take a minute on first run)...")
    try:
        markets = client.get_weather_markets()
        market_count = len(markets)
        if market_count == 0:
            print("[WARNING] No weather markets found. The bot will keep trying every 15 minutes.")
            print("[WARNING] This could mean Kalshi has no open weather markets right now.")
        else:
            print(f"[INIT] Locked onto {market_count} weather markets")
    except Exception as e:
        print(f"[FATAL] Could not fetch markets from Kalshi: {e}")
        sys.exit(1)

    # Initialize paper trade tracker
    paper_tracker = PaperTradeTracker()
    set_paper_tracker(paper_tracker)
    existing = len(paper_tracker.trades)
    if existing:
        print(f"[INIT] Paper tracker loaded ({existing} historical trades)")

    # Record bot start
    tracker.record_start()

    # Send startup Telegram message
    send_startup_message(config.PAPER_TRADING, market_count)
    print("[INIT] Startup message sent to Telegram")

    # Start Telegram command listener (background thread)
    start_command_listener()
    print("[INIT] Telegram command listener started")

    # Start morning report scheduler (background thread)
    start_morning_report_scheduler(tracker)
    print("[INIT] Morning report scheduler started (8 AM Central daily)")

    # Start end-of-day recap scheduler (background thread)
    start_eod_recap_scheduler(client, paper_tracker)
    print("[INIT] End-of-day recap scheduler started (8 PM Central daily)")

    # Hourly briefing disabled — too much noise. Whales-only via real-time alerts,
    # plus morning/evening reports for the full picture.
    # start_hourly_briefing_scheduler(detector)
    print("[INIT] Hourly briefing DISABLED (whales-only mode)")

    print("\n[RUNNING] Bot is now monitoring. Press Ctrl+C to stop.\n")

    # Main loop
    cycle = 0
    while True:
        cycle += 1
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        print(f"[Cycle {cycle}] {timestamp} — Scanning weather markets...")

        try:
            run_scan(client, detector, tracker, paper_tracker)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[ERROR] Scan cycle failed: {e}")
            send_error_message(f"Scan cycle {cycle} failed: {e}")
            tracker.record_error()

        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Bot stopped by user.")
