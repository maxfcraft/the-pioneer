"""
Daily activity tracker.

Keeps an in-memory log of everything the bot does each day so it can
answer questions like "what did you do today?" via Telegram commands
or in the automated morning report.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict


ACTIVITY_LOG_FILE = "daily_activity.json"


@dataclass
class DailyStats:
    """Accumulated stats for a single calendar day (UTC)."""
    date: str                          # "2026-03-18"
    scan_cycles: int = 0
    markets_scanned: int = 0
    total_trades_analyzed: int = 0
    whales_detected: int = 0
    copy_trades_placed: int = 0
    copy_trades_paper: int = 0
    errors: int = 0
    near_misses: list = field(default_factory=list)   # trades that were close to threshold
    whale_alerts: list = field(default_factory=list)   # summary of each whale found
    start_time: str = ""               # when bot started running this day
    last_cycle_time: str = ""          # timestamp of most recent cycle


class ActivityTracker:
    """Tracks bot activity per UTC day and persists to disk."""

    def __init__(self):
        self._days: dict[str, DailyStats] = {}
        self._load()

    def _today_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _today(self) -> DailyStats:
        key = self._today_key()
        if key not in self._days:
            self._days[key] = DailyStats(date=key)
        return self._days[key]

    # ── Recording events ──────────────────────────────────────────

    def record_cycle(self, markets_scanned: int, trades_analyzed: int):
        day = self._today()
        day.scan_cycles += 1
        day.markets_scanned = markets_scanned  # latest count
        day.total_trades_analyzed += trades_analyzed
        day.last_cycle_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self._save()

    def record_whale(self, ticker: str, title: str, count: int, side: str,
                     price_cents: int, multiplier: float, confidence: float,
                     trade_placed: bool, paper: bool):
        day = self._today()
        day.whales_detected += 1
        if trade_placed:
            day.copy_trades_placed += 1
        if paper:
            day.copy_trades_paper += 1
        day.whale_alerts.append({
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            "ticker": ticker,
            "title": title,
            "count": count,
            "side": side,
            "price_cents": price_cents,
            "multiplier": multiplier,
            "confidence": confidence,
            "trade_placed": trade_placed,
        })
        self._save()

    def record_near_miss(self, ticker: str, title: str, count: int,
                         rolling_avg: float, multiplier: float):
        """Track trades that reached at least 50% of the whale threshold."""
        day = self._today()
        # Keep only last 10 near misses to avoid bloat
        if len(day.near_misses) >= 10:
            day.near_misses.pop(0)
        day.near_misses.append({
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            "ticker": ticker,
            "title": title,
            "count": count,
            "rolling_avg": round(rolling_avg, 2),
            "multiplier": round(multiplier, 2),
        })

    def record_error(self):
        self._today().errors += 1
        self._save()

    def record_start(self):
        self._today().start_time = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
        self._save()

    # ── Querying ──────────────────────────────────────────────────

    def get_today(self) -> DailyStats:
        return self._today()

    def get_yesterday(self) -> DailyStats | None:
        key = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        return self._days.get(key)

    def get_day(self, date_str: str) -> DailyStats | None:
        return self._days.get(date_str)

    # ── Formatted reports ─────────────────────────────────────────

    def format_status_report(self) -> str:
        day = self._today()
        uptime = ""
        if day.start_time:
            uptime = f"Running since: {day.start_time}\n"

        report = (
            f"{'='*30}\n"
            f"BOT STATUS — {day.date}\n"
            f"{'='*30}\n"
            f"\n"
            f"{uptime}"
            f"Last scan: {day.last_cycle_time or 'N/A'}\n"
            f"Scan cycles: {day.scan_cycles}\n"
            f"Markets monitored: {day.markets_scanned}\n"
            f"Trades analyzed: {day.total_trades_analyzed}\n"
            f"\n"
            f"Whales detected: {day.whales_detected}\n"
            f"Copy trades (paper): {day.copy_trades_paper}\n"
            f"Copy trades (live): {day.copy_trades_placed}\n"
            f"Near misses: {len(day.near_misses)}\n"
            f"Errors: {day.errors}\n"
        )

        if day.whale_alerts:
            report += f"\nWhale Details:\n"
            for w in day.whale_alerts:
                report += (
                    f"  {w['time']} — {w['ticker']}\n"
                    f"    {w['count']} contracts {w['side'].upper()} @ {w['price_cents']}c "
                    f"({w['multiplier']}x, conf {w['confidence']})\n"
                )

        if day.near_misses:
            report += f"\nNearest Misses:\n"
            for nm in day.near_misses[-3:]:  # show last 3
                report += (
                    f"  {nm['time']} — {nm['ticker']}\n"
                    f"    {nm['count']} contracts vs avg {nm['rolling_avg']} "
                    f"({nm['multiplier']}x — needed {config_threshold()}x)\n"
                )

        return report

    def format_morning_report(self) -> str:
        """Generate the 7 AM morning summary for yesterday's activity."""
        yesterday = self.get_yesterday()
        today = self._today()

        if not yesterday:
            return (
                f"Good morning! No activity data from yesterday yet.\n"
                f"Bot is {'running' if today.scan_cycles > 0 else 'not running'}."
            )

        d = yesterday
        report = (
            f"{'='*30}\n"
            f"MORNING REPORT — {d.date}\n"
            f"{'='*30}\n"
            f"\n"
            f"Yesterday's Summary:\n"
            f"  Scan cycles completed: {d.scan_cycles}\n"
            f"  Markets monitored: {d.markets_scanned}\n"
            f"  Total trades analyzed: {d.total_trades_analyzed}\n"
            f"\n"
            f"  Whales detected: {d.whales_detected}\n"
            f"  Copy trades (paper): {d.copy_trades_paper}\n"
            f"  Copy trades (live): {d.copy_trades_placed}\n"
            f"  Errors: {d.errors}\n"
        )

        if d.whale_alerts:
            report += f"\nWhale Breakdown:\n"
            for w in d.whale_alerts:
                placed = "TRADED" if w['trade_placed'] else "alert only"
                report += (
                    f"  {w['time']} | {w['ticker']}\n"
                    f"    {w['count']} contracts {w['side'].upper()} @ {w['price_cents']}c\n"
                    f"    {w['multiplier']}x avg | confidence {w['confidence']} | {placed}\n"
                )
        else:
            report += "\n  No whales detected yesterday.\n"

        if d.near_misses:
            report += f"\nClosest Calls (almost triggered):\n"
            for nm in d.near_misses[-5:]:
                report += (
                    f"  {nm['ticker']} — {nm['count']} contracts "
                    f"({nm['multiplier']}x vs {config_threshold()}x threshold)\n"
                )

        # Today so far
        report += (
            f"\nToday so far:\n"
            f"  Bot is {'running' if today.scan_cycles > 0 else 'not running yet'}.\n"
            f"  Cycles: {today.scan_cycles} | Whales: {today.whales_detected}\n"
        )

        return report

    # ── Persistence ───────────────────────────────────────────────

    def _save(self):
        data = {}
        for key, stats in self._days.items():
            data[key] = asdict(stats)
        try:
            with open(ACTIVITY_LOG_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # non-critical, don't crash the bot

    def _load(self):
        if not os.path.exists(ACTIVITY_LOG_FILE):
            return
        try:
            with open(ACTIVITY_LOG_FILE, "r") as f:
                data = json.load(f)
            for key, vals in data.items():
                self._days[key] = DailyStats(**vals)
        except Exception:
            pass  # start fresh if corrupt


def config_threshold() -> float:
    """Get the whale threshold from config (import here to avoid circular)."""
    import config
    return config.WHALE_THRESHOLD_MULTIPLIER
