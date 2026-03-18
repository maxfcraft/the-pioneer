"""
Kalshi API client — handles authentication, market data, trade history, and order placement.

Kalshi v2 API uses RSA key signing: each request is signed with your private key
and verified by Kalshi using the public key you registered.
"""

import time
import datetime
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import requests

import config


class KalshiClient:
    """Wrapper around the Kalshi Trade API v2."""

    def __init__(self):
        self.base_url = config.KALSHI_BASE_URL
        self.api_key_id = config.KALSHI_API_KEY_ID
        self.private_key = self._load_private_key()
        self.session = requests.Session()

    def _load_private_key(self):
        """Load RSA private key from the PEM file specified in config."""
        with open(config.KALSHI_RSA_PRIVATE_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def _sign_request(self, method: str, path: str, timestamp_ms: int) -> str:
        """
        Create the RSA signature for a Kalshi API request.
        Signature covers: timestamp + method + path
        """
        message = f"{timestamp_ms}{method}{path}"
        signature = self.private_key.sign(
            message.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _build_headers(self, method: str, path: str) -> dict:
        """Build authenticated headers for a Kalshi API request."""
        timestamp_ms = int(time.time() * 1000)
        signature = self._sign_request(method, path, timestamp_ms)
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": str(timestamp_ms),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, params: dict = None, json_body: dict = None):
        """Make an authenticated request to the Kalshi API with retry on rate-limit."""
        url = f"{self.base_url}{path}"
        # Kalshi requires signing the full path (e.g. /trade-api/v2/portfolio/balance)
        full_path = "/trade-api/v2" + path

        max_retries = 4
        for attempt in range(max_retries + 1):
            headers = self._build_headers(method.upper(), full_path)
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
            if response.status_code == 429 and attempt < max_retries:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s, 16s
                print(f"[RATE-LIMIT] 429 received, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

    # ---- Market Data ----

    def get_events(self, status: str = "open", series_ticker: str = None,
                   cursor: str = None, limit: int = 100) -> dict:
        """Fetch events (groups of markets)."""
        params = {"status": status, "limit": limit}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/events", params=params)

    def get_markets(self, event_ticker: str = None, status: str = "open",
                    cursor: str = None, limit: int = 100) -> dict:
        """Fetch markets, optionally filtered by event ticker."""
        params = {"status": status, "limit": limit}
        if event_ticker:
            params["event_ticker"] = event_ticker
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/markets", params=params)

    def get_market(self, ticker: str) -> dict:
        """Fetch a single market by ticker."""
        return self._request("GET", f"/markets/{ticker}")

    def get_trades(self, ticker: str, cursor: str = None, limit: int = 100) -> dict:
        """
        Fetch recent trades for a specific market.
        Returns a list of trade objects with price, count (number of contracts),
        taker side (yes/no), and timestamp.
        """
        params = {"ticker": ticker, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/markets/trades", params=params)

    # ---- Order Placement ----

    def get_balance(self) -> dict:
        """Get account balance."""
        return self._request("GET", "/portfolio/balance")

    def place_order(self, ticker: str, side: str, count: int, price_cents: int,
                    order_type: str = "limit") -> dict:
        """
        Place an order on Kalshi.

        Args:
            ticker: Market ticker (e.g., "WEATHER-23-...")
            side: "yes" or "no"
            count: Number of contracts
            price_cents: Price per contract in cents (1-99)
            order_type: "limit" or "market"
        """
        body = {
            "ticker": ticker,
            "action": "buy",
            "side": side,
            "count": count,
            "type": order_type,
        }
        if order_type == "limit":
            body["yes_price"] = price_cents if side == "yes" else (100 - price_cents)

        return self._request("POST", "/portfolio/orders", json_body=body)

    # ---- Helper: Get Weather Markets ----

    def get_weather_markets(self) -> list:
        """
        Fetch all open markets whose ticker contains the MARKET_FILTER string.
        Paginates through all results.
        """
        all_markets = []
        cursor = None
        market_filter = config.MARKET_FILTER.upper()

        while True:
            data = self.get_markets(cursor=cursor, limit=200)
            markets = data.get("markets", [])
            for m in markets:
                if market_filter in m.get("ticker", "").upper():
                    all_markets.append(m)
            cursor = data.get("cursor")
            if not cursor or not markets:
                break
            time.sleep(0.5)  # pace requests to avoid 429 rate limits

        return all_markets
