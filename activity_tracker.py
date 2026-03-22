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
            f"SITUATION REPORT — {day.date}\n"
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

    @staticmethod
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
        # Fallback: strip KX prefix and return raw
        return ticker.split("-")[0].replace("KX", "")

    def format_morning_report(self) -> str:
        """Generate the 7 AM morning summary for yesterday's activity."""
        yesterday = self.get_yesterday()
        today = self._today()

        if not yesterday:
            return (
                f"Good morning, Master Bruce. No activity data from yesterday to report.\n"
                f"Systems are {'online and operational' if today.scan_cycles > 0 else 'standing by'}."
            )

        d = yesterday

        # --- City-level analysis ---
        city_whales: dict[str, list] = {}
        city_near_misses: dict[str, int] = {}
        city_total_contracts: dict[str, int] = {}

        for w in d.whale_alerts:
            city = self._city_from_ticker(w["ticker"])
            city_whales.setdefault(city, []).append(w)
            city_total_contracts[city] = city_total_contracts.get(city, 0) + w["count"]

        for nm in d.near_misses:
            city = self._city_from_ticker(nm["ticker"])
            city_near_misses[city] = city_near_misses.get(city, 0) + 1
            city_total_contracts[city] = city_total_contracts.get(city, 0) + nm["count"]

        # Find hottest city (most total whale + near-miss contract volume)
        hottest_city = max(city_total_contracts, key=city_total_contracts.get) if city_total_contracts else None

        report = (
            f"Good morning, Master Bruce.\n"
            f"\n"
            f"{'='*30}\n"
            f"MORNING BRIEFING — {d.date}\n"
            f"{'='*30}\n"
        )

        # --- Headline stats ---
        report += (
            f"\n"
            f"Whales: {d.whales_detected} | "
            f"Near misses: {len(d.near_misses)} | "
            f"Errors: {d.errors}\n"
        )

        if hottest_city:
            whale_count = len(city_whales.get(hottest_city, []))
            nm_count = city_near_misses.get(hottest_city, 0)
            contracts = city_total_contracts[hottest_city]
            report += (
                f"\nHottest city: {hottest_city}\n"
                f"  {whale_count} whales, {nm_count} near misses, "
                f"{contracts} total contracts\n"
            )

        # --- City breakdown ---
        if city_total_contracts:
            report += f"\nCity Breakdown:\n"
            for city in sorted(city_total_contracts, key=city_total_contracts.get, reverse=True):
                wcount = len(city_whales.get(city, []))
                nmcount = city_near_misses.get(city, 0)
                report += f"  {city}: {wcount} whales, {nmcount} near misses\n"

        # --- Whale details ---
        if d.whale_alerts:
            report += f"\nWhale Trades:\n"
            for w in d.whale_alerts:
                city = self._city_from_ticker(w["ticker"])
                cost = w["count"] * w["price_cents"] / 100
                placed = "PAPER TRADE" if w.get("trade_placed") else "alert only"
                report += (
                    f"  [{city}] {w['count']} contracts "
                    f"{w['side'].upper()} @ {w['price_cents']}c "
                    f"(${cost:.2f})\n"
                    f"    {w['multiplier']}x avg | conf {w['confidence']:.0f} | {placed}\n"
                )
        else:
            report += "\nNo whales detected yesterday. Quiet seas.\n"

        # --- Strategy notes ---
        report += f"\nStrategy Notes:\n"
        if d.whale_alerts:
            # Confidence breakdown
            high_conf = [w for w in d.whale_alerts if w["confidence"] >= 60]
            low_conf = [w for w in d.whale_alerts if w["confidence"] < 60]
            if high_conf and low_conf:
                report += (
                    f"  {len(high_conf)} high-confidence (60+) vs "
                    f"{len(low_conf)} low-confidence trades.\n"
                )
            # Average multiplier
            avg_mult = sum(w["multiplier"] for w in d.whale_alerts) / len(d.whale_alerts)
            report += f"  Average whale size: {avg_mult:.1f}x the rolling average.\n"
            # Biggest whale
            biggest = max(d.whale_alerts, key=lambda w: w["count"])
            report += (
                f"  Biggest whale: {biggest['count']} contracts in "
                f"{self._city_from_ticker(biggest['ticker'])} "
                f"({biggest['multiplier']}x avg).\n"
            )
        else:
            report += "  No whale data to analyze. Consider lowering threshold if this persists.\n"

        if len(d.near_misses) >= 5:
            report += (
                f"  {len(d.near_misses)} near misses — heavy positioning happening "
                f"just below threshold. Watch for follow-through today.\n"
            )

        # --- Today so far ---
        report += (
            f"\nSystems {'online' if today.scan_cycles > 0 else 'powering up'}. "
            f"Standing by, Master Bruce."
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
