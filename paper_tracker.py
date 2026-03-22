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
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_count = sum(1 for t in self.trades if t.timestamp.startswith(today))
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
        """Get all paper trades from today (UTC)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return [t for t in self.trades if t.timestamp.startswith(today)]

    def get_recent_trades(self, days: int = 7) -> list[PaperTrade]:
        """Get paper trades from the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        return [t for t in self.trades if t.timestamp >= cutoff]

    def format_recap(self, trades: list[PaperTrade] = None) -> str:
        """Format a recap message for Telegram."""
        if trades is None:
            trades = self.get_today_trades()

        if not trades:
            return ""

        total_pnl = sum(t.pnl_cents for t in trades)
        winners = [t for t in trades if t.pnl_cents > 0]
        losers = [t for t in trades if t.pnl_cents < 0]
        flat = [t for t in trades if t.pnl_cents == 0]

        recap = (
            f"{'='*30}\n"
            f"PAPER TRADE RECAP\n"
            f"{'='*30}\n\n"
        )

        for t in trades:
            pnl_dollars = t.pnl_cents / 100
            entry = t.entry_price_cents
            exit_p = t.exit_price_cents
            direction = "UP" if t.pnl_cents > 0 else "DOWN" if t.pnl_cents < 0 else "FLAT"
            status = "SETTLED" if t.resolved else "OPEN"
            label = f"  {t.codename} — " if t.codename else "  "

            recap += (
                f"{label}{t.market_ticker}\n"
                f"    {t.side.upper()} {t.contract_count} @ {entry}c -> {exit_p}c [{status}]\n"
                f"    Whale: {t.whale_multiplier}x | Conf: {t.confidence}\n"
                f"    P&L: ${pnl_dollars:+.2f} ({direction})\n\n"
            )

        total_dollars = total_pnl / 100
        total_cost = sum(t.cost_cents for t in trades) / 100
        roi = (total_pnl / max(sum(t.cost_cents for t in trades), 1)) * 100

        recap += (
            f"{'='*30}\n"
            f"SUMMARY\n"
            f"  Trades: {len(trades)} ({len(winners)}W / {len(losers)}L / {len(flat)}F)\n"
            f"  Total invested: ${total_cost:.2f}\n"
            f"  Net P&L: ${total_dollars:+.2f} ({roi:+.1f}%)\n"
            f"{'='*30}\n"
        )

        return recap

    # ---- Persistence ----

    def _save(self):
        try:
            data = [asdict(t) for t in self.trades]
            with open(PAPER_TRADES_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        if not os.path.exists(PAPER_TRADES_FILE):
            return
        try:
            with open(PAPER_TRADES_FILE, "r") as f:
                data = json.load(f)
            self.trades = [PaperTrade(**d) for d in data]
        except Exception:
            pass
