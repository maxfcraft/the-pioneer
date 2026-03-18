"""
Entry point. Run this to start the Auburn Blueprint automation bot.

Setup:
1. Copy .env.example to .env and fill in your credentials
2. pip install -r requirements.txt
3. playwright install chromium
4. python main.py

Then open Telegram and send /start to your bot.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from bot.telegram_bot import main

if __name__ == "__main__":
    main()
