"""
Whale detection engine.

Maintains a rolling window of recent trades per market and flags any single
trade whose contract count is >= WHALE_THRESHOLD_MULTIPLIER * rolling average.
"""

from collections import defaultdict, deque
from dataclasses import dataclass

import config


@dataclass
class WhaleAlert:
    """All the info about a detected whale trade."""
    market_ticker: str
    market_title: str
    trade_count: int          # number of contracts in the whale trade
    trade_price_cents: int    # price per contract in cents
    trade_side: str           # "yes" or "no"
    trade_total_cents: int    # count * price
    rolling_average: float    # average trade size over the window
    multiplier: float         # how many X above average this trade is
    confidence_score: float   # 0-100 score


class WhaleDetector:
    """
    Tracks trade history per market and detects whale trades.

    Usage:
        detector = WhaleDetector()
        alerts = detector.process_trades("TICKER", trades_list, "Market Title")
    """

    def __init__(self):
        # market_ticker -> deque of recent trade sizes (contract counts)
        self.trade_history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=config.ROLLING_WINDOW_SIZE)
        )
        # market_ticker -> set of trade IDs we already processed
        self.seen_trade_ids: dict[str, set] = defaultdict(set)
        # Recent near-miss trades (close to threshold but didn't trigger)
        self.last_near_misses: list = []

    def _calculate_rolling_average(self, ticker: str) -> float:
        """Calculate the average trade size for a market's rolling window."""
        history = self.trade_history[ticker]
        if not history:
            return 0.0
        return sum(history) / len(history)

    def _calculate_confidence(self, multiplier: float, history_size: int) -> float:
        """
        Confidence score from 0-100 based on:
        - How far above the threshold the trade is (higher = more confident)
        - How much history we have (more data = more confident)

        A trade that is exactly at threshold with a full window gets 50.
        Scores scale up from there.
        """
        # History factor: 0-1 based on how full our rolling window is
        history_factor = min(history_size / config.ROLLING_WINDOW_SIZE, 1.0)

        # Multiplier factor: how far above threshold (log scale would be better
        # but linear is fine for v1)
        threshold = config.WHALE_THRESHOLD_MULTIPLIER
        excess = (multiplier - threshold) / threshold  # 0 at threshold, 1 at 2x threshold
        multiplier_factor = min(excess + 0.5, 1.0)  # base 0.5 at threshold

        score = (history_factor * 0.4 + multiplier_factor * 0.6) * 100
        return round(min(max(score, 0), 100), 1)

    def process_trades(self, ticker: str, trades: list, market_title: str) -> list[WhaleAlert]:
        """
        Process a batch of trades for one market. Returns a list of WhaleAlerts
        for any trades that qualify as whale trades.

        Args:
            ticker: Market ticker string
            trades: List of trade dicts from the Kalshi API
            market_title: Human-readable market name
        """
        alerts = []
        seen = self.seen_trade_ids[ticker]

        # Sort trades oldest-first so rolling average builds chronologically
        sorted_trades = sorted(trades, key=lambda t: t.get("created_time", ""))

        for trade in sorted_trades:
            trade_id = trade.get("trade_id")
            if not trade_id or trade_id in seen:
                continue
            seen.add(trade_id)

            # Kalshi API v2 returns "count_fp" (string) and "yes_price_dollars" (string)
            count_raw = trade.get("count_fp", trade.get("count", 0))
            count = int(float(count_raw)) if count_raw else 0

            price_raw = trade.get("yes_price_dollars", trade.get("yes_price", 0.50))
            price_cents = int(float(price_raw) * 100) if price_raw else 50

            side = trade.get("taker_side", "unknown")

            rolling_avg = self._calculate_rolling_average(ticker)

            # Add this trade to history AFTER computing the average
            # (the whale trade itself should not inflate the average it's compared against)
            self.trade_history[ticker].append(count)

            # Need at least 10 trades of history to avoid false positives
            if len(self.trade_history[ticker]) < 10:
                continue

            if rolling_avg <= 0:
                continue

            multiplier = count / rolling_avg

            # Track near misses (50%+ of threshold but didn't trigger)
            if multiplier >= config.WHALE_THRESHOLD_MULTIPLIER * 0.5 and multiplier < config.WHALE_THRESHOLD_MULTIPLIER:
                self.last_near_misses.append({
                    "ticker": ticker,
                    "title": market_title,
                    "count": count,
                    "rolling_avg": rolling_avg,
                    "multiplier": multiplier,
                })
                # Keep only last 10
                if len(self.last_near_misses) > 10:
                    self.last_near_misses.pop(0)

            if multiplier >= config.WHALE_THRESHOLD_MULTIPLIER:
                confidence = self._calculate_confidence(
                    multiplier, len(self.trade_history[ticker])
                )
                alerts.append(WhaleAlert(
                    market_ticker=ticker,
                    market_title=market_title,
                    trade_count=count,
                    trade_price_cents=price_cents,
                    trade_side=side,
                    trade_total_cents=count * price_cents,
                    rolling_average=round(rolling_avg, 2),
                    multiplier=round(multiplier, 2),
                    confidence_score=confidence,
                ))

        return alerts
