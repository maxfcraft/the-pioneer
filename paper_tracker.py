"""
Paper trade tracker — records hypothetical trades and checks outcomes later.

When the bot detects a whale in paper mode, it records the entry price.
Later, it can check the current market price to calculate hypothetical P&L.
An end-of-day recap is sent via Telegram showing how each paper trade performed.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict

import config


PAPER_TRADES_FILE = "paper_trades.json"


def _central_today() -> str:
    """Get today's date string in Central Time (handles UTC offset correctly)."""
    utc_offset = config.MORNING_REPORT_UTC_OFFSET  # -5 for CDT, -6 for CST
    central_now = datetime.now(timezone(timedelta(hours=utc_offset)))
    return central_now.strftime("%Y-%m-%d")

# NATO phonetic alphabet for trade codenames
NATO_ALPHABET = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot",
    "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima",
    "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo",
    "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "X-Ray",
    "Yankee", "Zulu",
]


@dataclass
class PaperTrade:
    """A single hypothetical trade the bot would have placed."""
    timestamp: str              # ISO format UTC
    market_ticker: str
    market_title: str
    side: str                   # "yes" or "no"
    entry_price_cents: int      # price per contract at detection
    contract_count: int         # how many contracts we'd buy
    cost_cents: int             # total entry cost
    whale_multiplier: float     # how big the whale was
    confidence: float           # confidence score
    # Filled in later when we check outcome
    exit_price_cents: int = 0   # current/final price
    resolved: bool = False      # whether the market has settled or we checked
    pnl_cents: int = 0          # profit/loss in cents
    checked_at: str = ""        # when we last checked the price
    codename: str = ""          # NATO codename (e.g. "Trade Bravo")
    followup_sent: bool = False # whether 1-hour followup was sent


class PaperTradeTracker:
    """Tracks paper trades and calculates hypothetical P&L."""

    def __init__(self):
        self.trades: list[PaperTrade] = []
        self._load()

    def _next_codename(self) -> str:
        """Get the next NATO codename for today's trades."""
        today_count = len(self.get_today_trades())
        name = NATO_ALPHABET[today_count % len(NATO_ALPHABET)]
        return f"Trade {name}"

    def record_trade(self, ticker: str, title: str, side: str,
                     price_cents: int, count: int, multiplier: float,
                     confidence: float):
        """Record a new paper trade when a whale is detected."""
        codename = self._next_codename()
        trade = PaperTrade(
            timestamp=datetime.now(timezone.utc).isoformat(),
            market_ticker=ticker,
            market_title=title,
            side=side,
            entry_price_cents=price_cents,
            contract_count=count,
            cost_cents=count * price_cents,
            whale_multiplier=multiplier,
            confidence=confidence,
            codename=codename,
        )
        self.trades.append(trade)
        self._save()
        return trade

    def check_outcomes(self, client) -> list[PaperTrade]:
        """
        Check current prices for all unresolved paper trades.
        Returns list of trades that were updated.
        """
        updated = []
        for trade in self.trades:
            if trade.resolved:
                continue
            try:
                market_data = client.get_market(trade.market_ticker)
                market = market_data.get("market", market_data)

                # Check if market has settled
                status = market.get("status", "")
                result = market.get("result", "")

                if status == "settled" or result:
                    # Market resolved: yes=100c, no=0c (or vice versa)
                    if result == "yes":
                        current_price = 100
                    elif result == "no":
                        current_price = 0
                    else:
                        current_price = market.get("yes_price", market.get("last_price", trade.entry_price_cents))
                    trade.resolved = True
                else:
                    # Still open: use current yes_price
                    current_price = market.get("yes_price", market.get("last_price", trade.entry_price_cents))

                trade.exit_price_cents = current_price
                trade.checked_at = datetime.now(timezone.utc).isoformat()

                # Calculate P&L
                if trade.side == "yes":
                    pnl_per_contract = current_price - trade.entry_price_cents
                else:
                    # For "no" side: you profit when price goes down
                    pnl_per_contract = trade.entry_price_cents - current_price

                trade.pnl_cents = pnl_per_contract * trade.contract_count
                updated.append(trade)

            except Exception as e:
                print(f"[PAPER] Could not check {trade.market_ticker}: {e}")
                continue

        if updated:
            self._save()
        return updated

    def check_single_trade(self, trade: PaperTrade, client) -> PaperTrade | None:
        """Check the current price of a single trade for follow-up reporting."""
        try:
            market_data = client.get_market(trade.market_ticker)
            market = market_data.get("market", market_data)

            status = market.get("status", "")
            result = market.get("result", "")

            if status == "settled" or result:
                if result == "yes":
                    current_price = 100
                elif result == "no":
                    current_price = 0
                else:
                    current_price = market.get("yes_price", market.get("last_price", trade.entry_price_cents))
                trade.resolved = True
            else:
                current_price = market.get("yes_price", market.get("last_price", trade.entry_price_cents))

            trade.exit_price_cents = current_price
            trade.checked_at = datetime.now(timezone.utc).isoformat()

            if trade.side == "yes":
                pnl_per_contract = current_price - trade.entry_price_cents
            else:
                pnl_per_contract = trade.entry_price_cents - current_price

            trade.pnl_cents = pnl_per_contract * trade.contract_count
            trade.followup_sent = True
            self._save()
            return trade
        except Exception as e:
            print(f"[FOLLOWUP] Could not check {trade.market_ticker}: {e}")
            return None

    def get_today_trades(self) -> list[PaperTrade]:
        """Get all paper trades from today (Central Time)."""
        today = _central_today()
        # Trades are stored in UTC — convert each to Central for comparison
        utc_offset = config.MORNING_REPORT_UTC_OFFSET
        central_tz = timezone(timedelta(hours=utc_offset))
        result = []
        for t in self.trades:
            try:
                trade_utc = datetime.fromisoformat(t.timestamp)
                if trade_utc.tzinfo is None:
                    trade_utc = trade_utc.replace(tzinfo=timezone.utc)
                trade_central = trade_utc.astimezone(central_tz)
                if trade_central.strftime("%Y-%m-%d") == today:
                    result.append(t)
            except (ValueError, TypeError):
                # Fallback: prefix match on raw timestamp
                if t.timestamp.startswith(today):
                    result.append(t)
        return result

    def get_date_trades(self, date_str: str) -> list[PaperTrade]:
        """Get all paper trades for a specific Central Time date (YYYY-MM-DD)."""
        utc_offset = config.MORNING_REPORT_UTC_OFFSET
        central_tz = timezone(timedelta(hours=utc_offset))
        result = []
        for t in self.trades:
            try:
                trade_utc = datetime.fromisoformat(t.timestamp)
                if trade_utc.tzinfo is None:
                    trade_utc = trade_utc.replace(tzinfo=timezone.utc)
                trade_central = trade_utc.astimezone(central_tz)
                if trade_central.strftime("%Y-%m-%d") == date_str:
                    result.append(t)
            except (ValueError, TypeError):
                if t.timestamp.startswith(date_str):
                    result.append(t)
        return result

    def get_yesterday_trades(self) -> list[PaperTrade]:
        """Get all paper trades from yesterday (Central Time)."""
        utc_offset = config.MORNING_REPORT_UTC_OFFSET
        central_tz = timezone(timedelta(hours=utc_offset))
        yesterday = (datetime.now(central_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.get_date_trades(yesterday)

    def get_recent_trades(self, days: int = 7) -> list[PaperTrade]:
        """Get paper trades from the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return [t for t in self.trades if t.timestamp >= cutoff]

    def format_recap(self, trades: list[PaperTrade] = None) -> str:
        """Format a recap message for Telegram with $10 copy trade P&L."""
        if trades is None:
            trades = self.get_today_trades()

        if not trades:
            return ""

        copy_amount = config.PAPER_COPY_AMOUNT_CENTS / 100  # $10 default
        total_pnl = sum(t.pnl_cents for t in trades)
        winners = [t for t in trades if t.pnl_cents > 0]
        losers = [t for t in trades if t.pnl_cents < 0]
        flat = [t for t in trades if t.pnl_cents == 0]

        recap = (
            f"{'='*30}\n"
            f"PAPER TRADE RECAP (${copy_amount:.0f} copy)\n"
            f"{'='*30}\n\n"
        )

        for t in trades:
            pnl_dollars = t.pnl_cents / 100
            entry = t.entry_price_cents
            exit_p = t.exit_price_cents
            status = "SETTLED" if t.resolved else "OPEN"
            label = f"  {t.codename} — " if t.codename else "  "

            # ROI for this individual trade
            trade_roi = (t.pnl_cents / max(t.cost_cents, 1)) * 100

            recap += (
                f"{label}{t.market_title}\n"
                f"    {t.side.upper()} {t.contract_count} @ {entry}c -> {exit_p}c [{status}]\n"
                f"    Whale: {t.whale_multiplier}x | Conf: {t.confidence}/100\n"
                f"    ${copy_amount:.0f} copy -> ${pnl_dollars:+.2f} ({trade_roi:+.1f}%)\n\n"
            )

        total_dollars = total_pnl / 100
        total_cost = sum(t.cost_cents for t in trades) / 100
        roi = (total_pnl / max(sum(t.cost_cents for t in trades), 1)) * 100

        recap += (
            f"{'='*30}\n"
            f"BOTTOM LINE\n"
            f"  Trades: {len(trades)} ({len(winners)}W / {len(losers)}L / {len(flat)}F)\n"
            f"  Total risked: ${total_cost:.2f}\n"
            f"  Net P&L: ${total_dollars:+.2f} ({roi:+.1f}% ROI)\n"
        )

        # Show what a $10 per trade bankroll would look like
        if len(trades) > 1:
            total_deployed = copy_amount * len(trades)
            recap += f"  ${copy_amount:.0f}/trade x {len(trades)} trades = ${total_deployed:.0f} deployed\n"

        recap += f"{'='*30}\n"

        return recap

    # ---- Persistence ----

    def _save(self):
        try:
            data = [asdict(t) for t in self.trades]
            # Atomic write: write to temp file first, then rename
            tmp_file = PAPER_TRADES_FILE + ".tmp"
            with open(tmp_file, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_file, PAPER_TRADES_FILE)
        except Exception as e:
            print(f"[PAPER] ERROR saving trades: {e}")

    def _load(self):
        if not os.path.exists(PAPER_TRADES_FILE):
            return
        try:
            with open(PAPER_TRADES_FILE, "r") as f:
                data = json.load(f)
            self.trades = [PaperTrade(**d) for d in data]
        except Exception as e:
            print(f"[PAPER] ERROR loading trades: {e}")
