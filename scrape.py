"""
Auburn Blueprint Group Scraper
Run this. It finds every Auburn Facebook group and Reddit community it can,
then drops a full Excel sheet in the /exports folder.

Usage:
    python scrape.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from data.db import init_db, get_stats
from facebook.google_dorker import run_all_dorks
from reddit.reddit_finder import run_reddit_scan
from data.excel_exporter import export_to_excel


async def main():
    print("Auburn Blueprint Scraper")
    print("=" * 40)

    await init_db()

    # Phase 1 — Google/Bing/DDG dorking (no FB login needed)
    print("\n[1/3] Search engine dorking (Google, Bing, DuckDuckGo)...")
    print("      Finds FB groups that Facebook's own search hides.")
    dork_results = await run_all_dorks()
    print(f"      Done. {dork_results['unique_urls_found']} unique group URLs found.")

    # Phase 2 — Facebook search (requires FB login in .env)
    print("\n[2/3] Deep Facebook search (300+ term variations + chain discovery)...")
    fb_email = os.getenv("FB_EMAIL")
    fb_password = os.getenv("FB_PASSWORD")
    if not fb_email or not fb_password:
        print("      Skipped — FB_EMAIL and FB_PASSWORD not set in .env")
        print("      Add them to run Phase 2 and find 10x more groups.")
    else:
        try:
            from facebook.deep_group_finder import run_deep_facebook_scan
            fb_results = await run_deep_facebook_scan()
            if "error" in fb_results:
                print(f"      Warning: {fb_results['error']}")
            else:
                print(f"      Done. {fb_results['total_groups_saved']} groups from Facebook search.")
        except Exception as e:
            print(f"      Phase 2 error: {e}")
            print("      Skipping. Phase 1 and 3 results still saved.")

    # Phase 3 — Reddit
    print("\n[3/3] Reddit scan...")
    reddit_results = await run_reddit_scan()
    print(f"      Done. {reddit_results['total_subreddits']} subreddits, {reddit_results['total_posts']} posts.")

    # Export to Excel
    print("\nBuilding Excel sheet...")
    stats = await get_stats()
    filepath = await export_to_excel(reddit_results)

    print("\n" + "=" * 40)
    print("DONE")
    print(f"Facebook groups found: {stats['groups_found']}")
    print(f"Reddit subreddits:     {reddit_results['total_subreddits']}")
    print(f"Reddit posts:          {reddit_results['total_posts']}")
    print(f"\nExcel file: {filepath}")


if __name__ == "__main__":
    asyncio.run(main())
