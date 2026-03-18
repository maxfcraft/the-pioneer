"""
Kalshi API client — handles market data, trade history, and (optionally) order placement.

Public endpoints (markets, trades) work without authentication.
Private endpoints (balance, orders) require RSA key signing.
"""

import os
import time
import base64
import requests

import config


class KalshiClient:
    """Wrapper around the Kalshi Trade API v2."""

    def __init__(self):
        self.base_url = config.KALSHI_BASE_URL
        self.api_key_id = config.KALSHI_API_KEY_ID
        self.private_key = None
        self.authenticated = False
        self.session = requests.Session()

        # Try to load auth — not required for market monitoring
        if self.api_key_id and config.KALSHI_RSA_PRIVATE_KEY_PATH:
            try:
                self.private_key = self._load_private_key()
                self.authenticated = True
            except Exception as e:
                print(f"[AUTH] Could not load private key: {e}")
                print("[AUTH] Running in public-only mode (no balance/trading)")

    def _load_private_key(self):
        """Load RSA private key from the PEM file specified in config."""
        from cryptography.hazmat.primitives import serialization
        with open(config.KALSHI_RSA_PRIVATE_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def _sign_request(self, method: str, path: str, timestamp_ms: int) -> str:
        """Create the RSA signature for a Kalshi API request."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
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

    def _build_headers(self, method: str, path: str, auth: bool = False) -> dict:
        """Build request headers. Adds auth signatures only when needed and available."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if auth and self.authenticated:
            timestamp_ms = int(time.time() * 1000)
            signature = self._sign_request(method, path, timestamp_ms)
            headers["KALSHI-ACCESS-KEY"] = self.api_key_id
            headers["KALSHI-ACCESS-SIGNATURE"] = signature
            headers["KALSHI-ACCESS-TIMESTAMP"] = str(timestamp_ms)
        return headers

    def _request(self, method: str, path: str, params: dict = None,
                 json_body: dict = None, auth: bool = False):
        """Make a request to the Kalshi API with retry on rate-limit."""
        url = f"{self.base_url}{path}"
        full_path = "/trade-api/v2" + path

        max_retries = 4
        for attempt in range(max_retries + 1):
            headers = self._build_headers(method.upper(), full_path, auth=auth)
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
            if response.status_code == 429 and attempt < max_retries:
                wait = 2 ** (attempt + 1)
                print(f"[RATE-LIMIT] 429 received, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()

    # ---- Market Data (public — no auth required) ----

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
        """Fetch recent trades for a specific market (public endpoint)."""
        params = {"ticker": ticker, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "/markets/trades", params=params)

    # ---- Account (auth required) ----

    def get_balance(self) -> dict:
        """Get account balance (requires valid API key)."""
        if not self.authenticated:
            return {"balance": 0}
        return self._request("GET", "/portfolio/balance", auth=True)

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

        if not self.authenticated:
            raise RuntimeError("Cannot place orders without valid API key authentication")
        return self._request("POST", "/portfolio/orders", json_body=body, auth=True)

    # ---- Helper: Get Weather Markets ----

    def get_weather_markets(self) -> list:
        """
        Fetch all open markets whose ticker matches any of the MARKET_FILTER patterns.
        Supports comma-separated filters (e.g., "KXHIGH,KXRAIN,KXSNOW").
        Paginates through all results.
        """
        all_markets = []
        cursor = None
        filters = [f.strip().upper() for f in config.MARKET_FILTER.split(",") if f.strip()]

        while True:
            data = self.get_markets(cursor=cursor, limit=200)
            markets = data.get("markets", [])
            for m in markets:
                ticker_upper = m.get("ticker", "").upper()
                if any(f in ticker_upper for f in filters):
                    all_markets.append(m)
            cursor = data.get("cursor")
            if not cursor or not markets:
                break
            time.sleep(0.5)  # pace requests to avoid 429 rate limits

        return all_markets
