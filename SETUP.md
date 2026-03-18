# Auburn Blueprint Automation — Setup Guide

## What This Does

- **Telegram bot** on your phone = full control panel
- **Facebook Group Finder** = searches every Auburn group by city (Mobile, Huntsville, Birmingham, Atlanta, etc.)
- **Group Blaster** = posts city-personalized AI messages to each group (sounds human, not spam)
- **Marketplace Poster** = posts your $50 course listing so people searching "Auburn University" find you
- **DM Responder** = auto-replies to anyone who messages you with a 3-stage funnel sequence
- **Claude AI** = generates every message — local, human-sounding, specific to each city's high schools

---

## Step 1: Get Your Telegram Bot Token

1. Open Telegram, message `@BotFather`
2. Send `/newbot`, follow prompts, get your token
3. Message your new bot, then go to:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Copy your `chat_id` from the response

---

## Step 2: Get Your Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. You have Claude Pro — your API key is separate from the app subscription

---

## Step 3: Configure Your .env

```
cp .env.example .env
```

Edit `.env` with:
- Your Telegram bot token + your chat ID
- Your Facebook email + password
- Your Anthropic API key

---

## Step 4: Install Dependencies (Windows)

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Step 5: Run the Bot

```bash
python main.py
```

Open Telegram, message your bot `/start`.

---

## Daily Workflow

| Command | What it does |
|---|---|
| `/find_groups` | Scans Facebook for every Auburn group in AL/FL/GA (run once a week) |
| `/blast 5` | Posts to 5 new groups today — AI writes each one |
| `/check_dms` | Checks Messenger and auto-replies to leads |
| `/marketplace` | Posts a fresh Marketplace listing |
| `/stats` | Shows total groups, posts, DMs, conversions |
| `/preview Mobile` | See what the AI would post in a Mobile group before blasting |

---

## Anti-Ban Strategy

- Posts are spaced 3-8 minutes apart (randomized)
- All typing is human-speed with random delays
- Browser session is saved — logs in once, stays logged in
- Messages are AI-generated and unique each time — not copy-paste
- Limit to 5-10 group posts per day max

---

## Cities Covered

Alabama: Mobile, Huntsville, Birmingham, Montgomery, Tuscaloosa, Dothan, Decatur, Gadsden
Florida: Pensacola
Georgia: Atlanta (north suburbs)

Each city has its specific high schools baked in — the AI references them to sound local.
