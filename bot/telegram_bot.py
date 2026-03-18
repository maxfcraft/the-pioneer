"""
Telegram bot — your command center for the Auburn Blueprint automation.
Run this on your server (or Windows machine) and control everything from your phone.

Commands:
  /start        - Welcome message + command list
  /stats        - Show DB stats (groups found, posts made, DMs, conversions)
  /find_groups  - Scan Facebook for new Auburn groups (takes ~10-20 min)
  /blast [n]    - Post to next N unposted groups (default 3)
  /marketplace  - Post a new Marketplace listing
  /check_dms    - Check Messenger and auto-reply to new messages
  /preview [city] - Preview AI message for a city before blasting
  /status       - Check if Facebook session is active
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))


def authorized(func):
    """Decorator — only respond to your chat ID."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != AUTHORIZED_CHAT_ID:
            await update.message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


@authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = """Auburn Blueprint Automation Bot

Commands:
/stats — DB stats
/find_groups — Scan Facebook for Auburn groups
/blast [n] — Post to next N groups (default 3)
/marketplace — Create a Marketplace listing
/check_dms — Auto-reply to Facebook messages
/preview [city] — Preview AI post for a city
/status — Check Facebook login status

War Eagle!"""
    await update.message.reply_text(msg)


@authorized
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Fetching stats...")

    from data.db import get_stats
    stats = await get_stats()

    msg = f"""Auburn Blueprint Stats

Groups found: {stats['groups_found']}
Groups posted to: {stats['groups_posted']}
DM conversations: {stats['dm_conversations']}
Conversions (paid): {stats['converted']}
Active Marketplace listings: {stats['active_listings']}

Revenue estimate: ${stats['converted'] * 50}"""

    await update.message.reply_text(msg)


@authorized
async def cmd_find_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Starting Facebook group scan for all Alabama cities...\n"
        "This takes 10-20 minutes. I'll message you when done."
    )

    from facebook.group_finder import find_all_auburn_groups
    from data.db import init_db

    await init_db()
    results = await find_all_auburn_groups()

    if "error" in results:
        await update.message.reply_text(f"Error: {results['error']}")
        return

    total = sum(v for v in results.values() if isinstance(v, int))
    city_lines = "\n".join(f"  {city}: {count}" for city, count in results.items() if isinstance(count, int))

    await update.message.reply_text(
        f"Group scan complete!\n\nTotal found: {total}\n\n{city_lines}\n\nRun /blast to start posting."
    )


@authorized
async def cmd_blast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Parse optional limit argument
    limit = 3
    if context.args:
        try:
            limit = int(context.args[0])
            limit = min(limit, 10)  # Cap at 10 per run for safety
        except ValueError:
            pass

    await update.message.reply_text(
        f"Posting to {limit} groups now...\n"
        f"Each post has a 3-8 minute delay between them (avoids FB ban).\n"
        f"I'll update you when done."
    )

    from facebook.group_poster import blast_unposted_groups
    results = await blast_unposted_groups(limit)

    if "error" in results:
        await update.message.reply_text(f"Error: {results['error']}")
        return

    posted = results.get("posted", 0)
    failed = results.get("failed", 0)
    group_lines = "\n".join(
        f"  {'✓' if g['status'] == 'posted' else '✗'} {g['name']} ({g['city']})"
        for g in results.get("groups", [])
    )

    await update.message.reply_text(
        f"Blast complete!\n\nPosted: {posted}\nFailed: {failed}\n\n{group_lines}"
    )


@authorized
async def cmd_marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Creating Marketplace listing... (takes ~2 min)")

    from facebook.marketplace import post_marketplace_listing
    result = await post_marketplace_listing()

    if "error" in result:
        await update.message.reply_text(f"Failed: {result['error']}")
    else:
        await update.message.reply_text(
            f"Marketplace listing posted!\n\nTitle: {result['title']}\nURL: {result.get('url', 'posted')}"
        )


@authorized
async def cmd_check_dms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking Facebook Messenger for new messages...")

    from facebook.dm_responder import run_dm_responder
    result = await run_dm_responder()

    if "error" in result:
        await update.message.reply_text(f"Error: {result['error']}")
        return

    count = result.get("replies_sent", 0)
    if count == 0:
        await update.message.reply_text("No new messages to reply to.")
        return

    lines = [f"  - {d['user']}: '{d['their_message'][:40]}...'" for d in result.get("details", [])]
    await update.message.reply_text(
        f"Replied to {count} conversations:\n\n" + "\n".join(lines)
    )


@authorized
async def cmd_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = " ".join(context.args) if context.args else "Mobile"

    from ai.message_generator import generate_group_post
    from config.cities import ALABAMA_CITIES

    city_data = next((c for c in ALABAMA_CITIES if c["city"].lower() == city.lower()), None)
    if not city_data:
        await update.message.reply_text(f"City '{city}' not found. Try: Mobile, Huntsville, Birmingham, Montgomery, Dothan, Atlanta, Pensacola")
        return

    await update.message.reply_text(f"Generating preview for {city}...")
    msg = generate_group_post(
        city_data["city"],
        city_data["state"],
        city_data["high_schools"],
        f"Auburn University {city} Parents Group",
    )
    await update.message.reply_text(f"--- PREVIEW for {city} ---\n\n{msg}")


@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking Facebook session...")

    from facebook.browser import FacebookBrowser
    async with FacebookBrowser() as fb:
        await fb.start(headless=True)
        logged_in = await fb.is_logged_in()

    status = "Logged in and active" if logged_in else "NOT logged in — run /login or check credentials"
    await update.message.reply_text(f"Facebook status: {status}")


def main():
    """Start the Telegram bot."""
    from data.db import init_db

    # Initialize database
    asyncio.get_event_loop().run_until_complete(init_db())

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("find_groups", cmd_find_groups))
    app.add_handler(CommandHandler("blast", cmd_blast))
    app.add_handler(CommandHandler("marketplace", cmd_marketplace))
    app.add_handler(CommandHandler("check_dms", cmd_check_dms))
    app.add_handler(CommandHandler("preview", cmd_preview))
    app.add_handler(CommandHandler("status", cmd_status))

    print("Auburn Blueprint Bot is running. Send /start in Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
