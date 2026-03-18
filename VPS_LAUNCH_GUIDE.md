# VPS Launch Guide — Kalshi Whale Bot (A to Z)

This guide assumes you have a Windows VPS via Remote Desktop Connection (RDP).
Follow every step in order.

---

## STEP 1: Open Your VPS

1. On your computer, press **Windows key**, type **Remote Desktop Connection**, open it
2. Enter your VPS IP address (the one your VPS provider gave you)
3. Enter username and password
4. You should now see a Windows desktop — this is your VPS

---

## STEP 2: Install Python

1. Open **Microsoft Edge** (or any browser) on the VPS
2. Go to: https://www.python.org/downloads/
3. Click the big yellow **"Download Python 3.x.x"** button
4. Run the installer
5. **IMPORTANT**: Check the box that says **"Add Python to PATH"** at the bottom
6. Click **Install Now**
7. Wait for it to finish, click Close

**Verify it worked:**
1. Press **Windows key**, type **cmd**, open **Command Prompt**
2. Type: `python --version`
3. You should see something like `Python 3.12.x`
4. Type: `pip --version`
5. You should see something like `pip 24.x.x`

If you see errors, restart the VPS and try again.

---

## STEP 3: Install Git

1. In the browser on your VPS, go to: https://git-scm.com/download/win
2. Download the installer (64-bit)
3. Run it — click **Next** through everything (defaults are fine)
4. Finish the install

**Verify:**
1. Open a NEW Command Prompt (close the old one, open fresh)
2. Type: `git --version`
3. Should show `git version 2.x.x`

---

## STEP 4: Clone the Code (Download It From GitHub)

"Clone" just means "download the code from GitHub to your VPS."

1. Open Command Prompt
2. Navigate to where you want the bot to live. I recommend the Desktop:

```
cd Desktop
```

3. Clone the repository:

```
git clone https://github.com/maxfcraft/the-pioneer.git
```

4. Enter the folder:

```
cd the-pioneer
```

You should now see all the bot files if you type `dir`.

---

## STEP 5: Install Python Dependencies

Still in Command Prompt, inside the `the-pioneer` folder:

```
pip install -r requirements.txt
```

This installs the 3 libraries the bot needs (requests, python-dotenv, cryptography).

---

## STEP 6: Set Up Your Secrets (.env file)

The code already has a `.env.example` template. You need to create the real `.env` file.

1. Copy the template:

```
copy .env.example .env
```

2. Open the .env file in Notepad:

```
notepad .env
```

3. Fill in your real values:

```
KALSHI_API_KEY_ID=your-actual-kalshi-api-key
KALSHI_RSA_PRIVATE_KEY_PATH=./kalshi_private_key.pem
TELEGRAM_BOT_TOKEN=your-actual-telegram-bot-token
TELEGRAM_CHAT_ID=your-actual-chat-id
```

Leave everything else as default for now. Save and close Notepad.

**Where to get these values:**
- **KALSHI_API_KEY_ID**: Log into Kalshi > Settings > API Keys
- **TELEGRAM_BOT_TOKEN**: Message @BotFather on Telegram > /newbot > copy the token
- **TELEGRAM_CHAT_ID**: Message @userinfobot on Telegram > it replies with your ID

---

## STEP 7: Add Your Kalshi Private Key

You need the `.pem` file from Kalshi (the RSA private key you downloaded when creating your API key).

1. Copy your `kalshi_private_key.pem` file into the `the-pioneer` folder on the VPS Desktop
2. You can drag-and-drop it via Remote Desktop, or download it from wherever you saved it

**Verify:** In Command Prompt, type:
```
dir kalshi_private_key.pem
```
It should show the file. If not, the file is in the wrong place.

---

## STEP 8: Test Run the Bot

Now the moment of truth. In Command Prompt, inside the `the-pioneer` folder:

```
python main.py
```

**What you should see:**

```
==================================================
  KALSHI WEATHER WHALE BOT
  Mode: PAPER TRADING
  Threshold: 10x average
  Portfolio risk: 15% per trade
  Poll interval: 30s
  Market filter: WEATHER
==================================================

[INIT] Connecting to Kalshi API...
[INIT] Found XX weather markets
[INIT] Startup message sent to Telegram
[INIT] Telegram command listener started
[INIT] Morning report scheduler started (7 AM daily)

[RUNNING] Bot is now monitoring. Press Ctrl+C to stop.

[Cycle 1] HH:MM:SS UTC — Scanning WEATHER markets...
  Portfolio balance: $XX.XX
  No whales this cycle
```

**Check your phone:** You should get a Telegram message from your bot saying it started.

**Test the commands:** Open Telegram, message your bot:
- Type `/status` — should reply with bot status
- Type `/balance` — should reply with your Kalshi balance
- Type `/help` — should list all commands

**If it works:** Press **Ctrl+C** to stop it. We'll set it up to run permanently next.

**If it errors:** Read the error message carefully. Common issues:
- "Missing required config" — your .env file is missing values
- "RSA private key file not found" — .pem file is in wrong location
- "Failed to connect to Kalshi API" — API key or private key is wrong
- "TELEGRAM ERROR" — bot token or chat ID is wrong

---

## STEP 9: Run It Permanently (Survives Disconnect)

When you close Remote Desktop, you want the bot to keep running.

**Option A: Using `start /b` (simplest)**

```
start /b python main.py > bot_output.log 2>&1
```

This runs the bot in the background and saves all output to `bot_output.log`.

To check the log later:
```
type bot_output.log
```

To stop the bot:
```
taskkill /f /im python.exe
```

**Option B: Create a batch file (recommended)**

1. Create a file called `start_bot.bat`:

```
notepad start_bot.bat
```

2. Paste this content:

```
@echo off
echo Starting Kalshi Whale Bot...
cd /d %~dp0
python main.py
pause
```

3. Save and close

4. Double-click `start_bot.bat` to run the bot
5. It opens in its own Command Prompt window
6. Just minimize it — don't close it

**Option C: Run as a Windows Service (most robust)**

If you want it to auto-start when the VPS reboots:

1. Open Task Scheduler (Windows key > type "Task Scheduler")
2. Click "Create Basic Task"
3. Name it "Kalshi Whale Bot"
4. Trigger: "When the computer starts"
5. Action: "Start a program"
6. Program: `python`
7. Arguments: `main.py`
8. Start in: `C:\Users\YOUR_USERNAME\Desktop\the-pioneer`
9. Finish

Now the bot auto-starts every time the VPS reboots.

---

## STEP 10: Pull Updates (When I Push New Code)

When I make changes and push to GitHub, you pull them on your VPS:

```
cd Desktop\the-pioneer
git pull origin main
```

Then restart the bot (Ctrl+C the old one, run `python main.py` again).

---

## Quick Reference

| What | Command |
|------|---------|
| Start the bot | `python main.py` |
| Stop the bot | `Ctrl+C` or `taskkill /f /im python.exe` |
| Check bot status | Send `/status` to your Telegram bot |
| Check balance | Send `/balance` to your Telegram bot |
| View today's activity | Send `/today` to your Telegram bot |
| View yesterday | Send `/yesterday` to your Telegram bot |
| Pull updates | `git pull origin main` |
| Check logs | `type bot_output.log` |
| View trade history | Open `whale_trades.csv` in Excel |

---

## What the Bot Does Once Running

- Scans all Kalshi weather markets every 30 seconds
- Tracks every trade and builds rolling averages
- When someone makes a trade 10x bigger than average = WHALE DETECTED
- Sends you an instant Telegram alert
- In paper mode: tells you what it WOULD trade (no real money)
- In live mode: automatically places a copy trade
- Every morning at 7 AM: sends you a full summary of yesterday
- You can ask it for updates anytime via Telegram commands
