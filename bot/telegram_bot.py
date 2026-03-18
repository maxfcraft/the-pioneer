"""
Telegram bot — command center for Auburn Blueprint automation.

Commands:
  /start          - Welcome + command list
  /stats          - DB stats (groups, posts, DMs, revenue)
  /deep_scan      - Full scan: Google dorks + 300 FB searches + Reddit (1-2 hrs)
  /dork           - Google/Bing/DDG dork only (fast, ~20 min)
  /reddit_scan    - Reddit scan only (~5 min)
  /blast [n]      - Post to next N groups (default 3)
  /marketplace    - Create Marketplace listing
  /check_dms      - Auto-reply to Facebook messages
  /export         - Export everything to Excel file
  /preview [city] - Preview AI post for a city
  /status         - Check Facebook login
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))


def authorized(func):
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

DISCOVERY:
/deep_scan — Full scan: Google dorks + 300 FB searches + Reddit (finds hundreds of groups)
/dork — Google/Bing/DDG only (fast, no FB login needed)
/reddit_scan — Reddit communities + posts

POSTING:
/blast [n] — Post to next N groups (default 3, max 10/day)
/marketplace — Create Marketplace listing
/check_dms — Auto-reply to Facebook DMs

REPORTING:
/export — Download full Excel spreadsheet
/stats — Live stats summary
/preview [city] — Preview AI message before blasting

SETUP:
/status — Check Facebook login"""
    await update.message.reply_text(msg)


@authorized
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from data.db import get_stats
    stats = await get_stats()
    conv_rate = f"{(stats['converted']/stats['dm_conversations']*100):.1f}%" if stats["dm_conversations"] else "N/A"
    msg = (
        f"Auburn Blueprint Stats\n\n"
        f"Facebook Groups Found: {stats['groups_found']}\n"
        f"Groups Posted To: {stats['groups_posted']}\n"
        f"Groups Remaining: {stats['groups_found'] - stats['groups_posted']}\n\n"
        f"DM Conversations: {stats['dm_conversations']}\n"
        f"Conversions: {stats['converted']}\n"
        f"Conversion Rate: {conv_rate}\n"
        f"Revenue: ${stats['converted'] * 50}\n\n"
        f"Active Marketplace Listings: {stats['active_listings']}"
    )
    await update.message.reply_text(msg)


@authorized
async def cmd_dork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Google/Bing/DDG dork — finds FB groups search engines have indexed."""
    await update.message.reply_text(
        "Starting Google/Bing/DuckDuckGo dork scan...\n"
        "No FB login needed. Hits all 3 search engines with 50+ Auburn queries.\n"
        "Takes ~15-20 min. Will update you every 10 queries."
    )

    from facebook.google_dorker import run_all_dorks

    async def progress(msg):
        await update.message.reply_text(msg)

    results = await run_all_dorks(progress_callback=progress)
    await update.message.reply_text(
        f"Dork scan complete!\n\n"
        f"Queries run: {results['queries_run']}\n"
        f"Unique group URLs found: {results['unique_urls_found']}\n"
        f"Saved to DB: {results['saved_to_db']}\n\n"
        f"Run /blast to start posting, or /export for the full list."
    )


@authorized
async def cmd_reddit_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Scanning Reddit for Auburn communities and posts...\n"
        "Checks r/AuburnUniversity, city subs (r/Birmingham, r/Huntsville, etc.), parent subs.\n"
        "Takes ~5 min."
    )

    from reddit.reddit_finder import run_reddit_scan
    results = await run_reddit_scan()

    await update.message.reply_text(
        f"Reddit scan complete!\n\n"
        f"Subreddits found: {results['total_subreddits']}\n"
        f"Posts to engage with: {results['total_posts']}\n\n"
        f"Run /export to get the full Excel sheet with all Reddit links."
    )

    # Store results for export
    context.bot_data["reddit_results"] = results


@authorized
async def cmd_deep_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full scan — everything at once. Takes 1-2 hours. Finds hundreds of groups."""
    await update.message.reply_text(
        "DEEP SCAN STARTED\n\n"
        "Phase 1: Google/Bing/DDG dorking (~20 min)\n"
        "Phase 2: Facebook search — 300+ term variations (~60-90 min)\n"
        "Phase 3: Related groups chaining\n"
        "Phase 4: Reddit scan (~5 min)\n\n"
        "I'll update you between phases. Go touch grass."
    )

    from facebook.google_dorker import run_all_dorks
    from facebook.deep_group_finder import run_deep_facebook_scan
    from reddit.reddit_finder import run_reddit_scan

    # Phase 1
    await update.message.reply_text("Phase 1/4: Dorking search engines...")
    dork_results = await run_all_dorks()
    await update.message.reply_text(
        f"Phase 1 done. Found {dork_results['unique_urls_found']} groups via dorks."
    )

    # Phase 2 + 3
    await update.message.reply_text("Phase 2/4: Facebook deep search (300+ terms + chain discovery)...")

    async def fb_progress(msg):
        await update.message.reply_text(msg)

    fb_results = await run_deep_facebook_scan(progress_callback=fb_progress)
    await update.message.reply_text(
        f"Phase 2+3 done. {fb_results['total_groups_saved']} groups from FB search."
    )

    # Phase 4
    await update.message.reply_text("Phase 4/4: Reddit scan...")
    reddit_results = await run_reddit_scan()
    context.bot_data["reddit_results"] = reddit_results
    await update.message.reply_text(
        f"Phase 4 done. {reddit_results['total_subreddits']} subreddits, {reddit_results['total_posts']} posts."
    )

    # Final summary
    from data.db import get_stats
    stats = await get_stats()
    await update.message.reply_text(
        f"DEEP SCAN COMPLETE\n\n"
        f"Total Facebook groups in DB: {stats['groups_found']}\n"
        f"Reddit subreddits: {reddit_results['total_subreddits']}\n"
        f"Reddit posts: {reddit_results['total_posts']}\n\n"
        f"Run /export for the full Excel sheet.\n"
        f"Run /blast 5 to start posting."
    )


@authorized
async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Building Excel spreadsheet... (~30 sec)")

    from data.excel_exporter import export_to_excel

    reddit_data = context.bot_data.get("reddit_results")
    filepath = await export_to_excel(reddit_data)

    await update.message.reply_document(
        document=open(filepath, "rb"),
        filename=filepath.split("/")[-1],
        caption=(
            "Full Auburn Blueprint outreach sheet.\n\n"
            "Sheets: Stats Dashboard | Facebook Groups | Posts Made | DM Funnel | Reddit Subreddits | Reddit Posts"
        ),
    )


@authorized
async def cmd_blast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = 3
    if context.args:
        try:
            limit = min(int(context.args[0]), 10)
        except ValueError:
            pass

    await update.message.reply_text(
        f"Posting to {limit} groups (3-8 min delay between each)...\nI'll report back when done."
    )

    from facebook.group_poster import blast_unposted_groups
    results = await blast_unposted_groups(limit)

    if "error" in results:
        await update.message.reply_text(f"Error: {results['error']}")
        return

    lines = [
        f"  {'OK' if g['status'] == 'posted' else 'FAIL'} — {g['name']} ({g['city']})"
        for g in results.get("groups", [])
    ]
    await update.message.reply_text(
        f"Blast done.\n\nPosted: {results['posted']} | Failed: {results['failed']}\n\n" + "\n".join(lines)
    )


@authorized
async def cmd_marketplace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Creating Marketplace listing...")
    from facebook.marketplace import post_marketplace_listing
    result = await post_marketplace_listing()
    if "error" in result:
        await update.message.reply_text(f"Failed: {result['error']}")
    else:
        await update.message.reply_text(f"Marketplace listing posted!\n{result.get('url', '')}")


@authorized
async def cmd_check_dms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking Facebook Messenger...")
    from facebook.dm_responder import run_dm_responder
    result = await run_dm_responder()
    if "error" in result:
        await update.message.reply_text(f"Error: {result['error']}")
        return
    count = result.get("replies_sent", 0)
    if count == 0:
        await update.message.reply_text("No new messages.")
        return
    lines = [f"  {d['user']}: '{d['their_message'][:40]}'" for d in result.get("details", [])]
    await update.message.reply_text(f"Replied to {count} messages:\n" + "\n".join(lines))


@authorized
async def cmd_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = " ".join(context.args) if context.args else "Mobile"
    from ai.message_generator import generate_group_post
    from config.search_terms import CITIES
    city_data = next((c for c in CITIES if c["city"].lower() == city.lower()), None)
    if not city_data:
        city_list = ", ".join(c["city"] for c in CITIES)
        await update.message.reply_text(f"City not found. Options: {city_list}")
        return
    await update.message.reply_text(f"Generating preview for {city}...")
    msg = generate_group_post(city_data["city"], city_data["state"], city_data["high_schools"], f"Auburn {city} Parents")
    await update.message.reply_text(f"--- {city} PREVIEW ---\n\n{msg}")


@authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking Facebook session...")
    from facebook.browser import FacebookBrowser
    async with FacebookBrowser() as fb:
        await fb.start(headless=True)
        logged_in = await fb.is_logged_in()
    status = "Logged in" if logged_in else "NOT logged in — check FB credentials in .env"
    await update.message.reply_text(f"Facebook: {status}")


def main():
    from data.db import init_db
    asyncio.get_event_loop().run_until_complete(init_db())

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("dork", cmd_dork))
    app.add_handler(CommandHandler("reddit_scan", cmd_reddit_scan))
    app.add_handler(CommandHandler("deep_scan", cmd_deep_scan))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("blast", cmd_blast))
    app.add_handler(CommandHandler("marketplace", cmd_marketplace))
    app.add_handler(CommandHandler("check_dms", cmd_check_dms))
    app.add_handler(CommandHandler("preview", cmd_preview))
    app.add_handler(CommandHandler("status", cmd_status))

    print("Auburn Blueprint Bot running. Send /start in Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
