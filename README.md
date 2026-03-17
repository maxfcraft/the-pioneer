# Kalshi Weather Whale Bot

Monitors Kalshi weather prediction markets in real time, detects whale trades (large positions significantly above average), sends Telegram alerts, and optionally copies the trade at a configurable fraction.

## Prerequisites

- Python 3.10+
- A funded, verified [Kalshi](https://kalshi.com) account with API key access
- A Telegram bot (created via [@BotFather](https://t.me/BotFather))

## Setup

### 1. Clone and install dependencies

```bash
cd the-pioneer
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your real credentials:

- `KALSHI_API_KEY_ID` — your Kalshi API key ID
- `KALSHI_RSA_PRIVATE_KEY_PATH` — path to your RSA private key PEM file (default: `./kalshi_private_key.pem`)
- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `TELEGRAM_CHAT_ID` — your Telegram user ID (from @userinfobot)

### 3. Save your Kalshi private key

When you generated your Kalshi API key, you received an RSA private key. Save it to a file:

```bash
# Paste your private key into this file
nano kalshi_private_key.pem
```

The file should start with `-----BEGIN RSA PRIVATE KEY-----` and end with `-----END RSA PRIVATE KEY-----`.

### 4. Run the bot

```bash
python main.py
```

The bot starts in **paper trading mode** by default (no real trades placed, only alerts).

## Configuration

All settings are in `.env`. Key options:

| Setting | Default | Description |
|---|---|---|
| `PAPER_TRADING` | `true` | Set to `false` to enable real trades |
| `WHALE_THRESHOLD_MULTIPLIER` | `10` | Trade must be Nx above average to trigger |
| `ROLLING_WINDOW_SIZE` | `100` | Number of recent trades for the average |
| `COPY_TRADE_FRACTION` | `0.10` | Copy 10% of the whale's position size |
| `MIN_TRADE_SIZE_CENTS` | `100` | Skip copy trades smaller than $1.00 |
| `POLL_INTERVAL_SECONDS` | `30` | How often to check for new trades |
| `MARKET_FILTER` | `WEATHER` | Only monitor markets with this in the ticker |

## Files

- `main.py` — Entry point, runs the monitoring loop
- `kalshi_client.py` — Kalshi API wrapper (auth, markets, trades, orders)
- `whale_detector.py` — Rolling average whale detection engine
- `telegram_bot.py` — Telegram notification sender
- `config.py` — Loads all settings from environment variables
- `whale_trades.csv` — Auto-generated log of all detected whales and trades

## Paper Trading Mode

The bot starts with `PAPER_TRADING=true`. In this mode:
- Whale detection runs normally
- Telegram alerts are sent for every whale detected
- No real orders are placed on Kalshi
- The CSV log records what would have been traded

Once you are confident the bot is working correctly, set `PAPER_TRADING=false` in `.env` to go live.
