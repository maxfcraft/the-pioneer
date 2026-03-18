"""
Deep Facebook group scraper. Three techniques stacked:
1. FB search with 300+ term variations
2. "Related groups" sidebar chain — find one group, discover 10 more
3. Member profile scanning — look at what other groups Auburn-bound students are in
"""

import asyncio
import random
import re
from playwright.async_api import Page
from facebook.browser import FacebookBrowser, human_delay
from data.db import save_group
from config.search_terms import build_fb_search_terms

FB_GROUP_PATTERN = re.compile(r"facebook\.com/groups/([a-zA-Z0-9._-]+)")


async def scrape_group_urls_from_page(page: Page) -> list[str]:
    """Extract all unique FB group URLs from current page."""
    found = set()
    html = await page.content()
    for m in FB_GROUP_PATTERN.finditer(html):
        group_id = m.group(1)
        if group_id not in ("feed", "discover", "create", "joins", "requests", "search", "suggests"):
            found.add(f"https://www.facebook.com/groups/{group_id}")
    return list(found)


async def fb_search_groups(page: Page, term: str, city: str, state: str, high_schools: list) -> int:
    """Search Facebook groups for a term, scroll to get all results, save to DB."""
    saved = 0
    encoded = term.replace(" ", "%20")
    await page.goto(f"https://www.facebook.com/search/groups/?q={encoded}")
    await human_delay(2000, 3500)

    # Scroll 5 times to load more results
    for _ in range(5):
        await page.keyboard.press("End")
        await human_delay(800, 1500)

    urls = await scrape_group_urls_from_page(page)

    # Try to get group names from the cards
    for url in urls:
        group_id = url.rstrip("/").split("/")[-1]
        # Attempt to read the name from an anchor near this URL
        try:
            elem = await page.query_selector(f"a[href*='/groups/{group_id}']")
            text = await elem.inner_text() if elem else ""
            group_name = text.strip()[:120] or f"Auburn Group — {group_id}"
        except Exception:
            group_name = f"Auburn Group — {group_id}"

        await save_group(group_name, url, city, state, "|".join(high_schools))
        saved += 1

    return saved


async def follow_related_groups(page: Page, seed_url: str, city: str, state: str, depth: int = 2) -> int:
    """
    Visit a group and follow its 'Related groups' sidebar to chain-discover more.
    depth=2 means we go 2 hops out from the seed.
    """
    visited = {seed_url}
    queue = [(seed_url, 0)]
    saved = 0

    while queue:
        url, current_depth = queue.pop(0)
        if current_depth > depth:
            continue

        try:
            await page.goto(url)
            await human_delay(2000, 4000)

            # Scroll down to load sidebar
            await page.evaluate("window.scrollTo(0, 500)")
            await human_delay(1000, 2000)

            related_urls = await scrape_group_urls_from_page(page)

            for related_url in related_urls:
                if related_url not in visited:
                    visited.add(related_url)
                    group_id = related_url.rstrip("/").split("/")[-1]
                    group_name = f"Auburn Group (discovered) — {group_id}"
                    await save_group(group_name, related_url, city, state)
                    saved += 1
                    if current_depth + 1 <= depth:
                        queue.append((related_url, current_depth + 1))

        except Exception as e:
            print(f"  Error visiting {url}: {e}")

        await asyncio.sleep(random.uniform(2, 5))

    return saved


async def run_deep_facebook_scan(progress_callback=None) -> dict:
    """
    Full deep scan:
    1. 300+ term searches
    2. Related groups chaining from top hits
    """
    search_terms = build_fb_search_terms()
    total_saved = 0
    seed_groups = []  # Collect good groups to chain from

    async with FacebookBrowser() as fb:
        await fb.start(headless=True)

        logged_in = await fb.is_logged_in()
        if not logged_in:
            import os
            logged_in = await fb.login(os.getenv("FB_EMAIL"), os.getenv("FB_PASSWORD"))
            if not logged_in:
                return {"error": "Facebook login failed"}

        page = fb.page

        # Phase 1: Search all terms
        for i, term_data in enumerate(search_terms):
            term = term_data["term"]
            city = term_data["city"]
            state = term_data["state"]
            schools = term_data.get("high_schools", [])

            if progress_callback and i % 20 == 0:
                pct = int((i / len(search_terms)) * 100)
                await progress_callback(f"FB Search [{pct}%] — {term[:50]}")

            count = await fb_search_groups(page, term, city, state, schools)
            total_saved += count

            # Collect seed URLs for chaining
            if count > 0:
                from data.db import get_unposted_groups
                seeds = await get_unposted_groups(3)
                for s in seeds:
                    seed_groups.append((s[2], s[3], s[4]))  # url, city, state

            # Delay between searches — critical to avoid rate limiting
            await asyncio.sleep(random.uniform(4, 8))

        # Phase 2: Chain discovery from seed groups (top 20 unique)
        if progress_callback:
            await progress_callback(f"Starting chain discovery from {len(seed_groups)} seed groups...")

        seen_seeds = set()
        for seed_url, city, state in seed_groups[:20]:
            if seed_url in seen_seeds:
                continue
            seen_seeds.add(seed_url)
            chained = await follow_related_groups(page, seed_url, city, state, depth=1)
            total_saved += chained
            await asyncio.sleep(random.uniform(3, 6))

    return {
        "terms_searched": len(search_terms),
        "total_groups_saved": total_saved,
        "seed_groups_chained": len(seen_seeds),
    }
