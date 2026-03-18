"""
Google/Bing/DuckDuckGo dorking to find Facebook groups that Facebook's own
search hides. Search engines index public FB groups independently.

This is the biggest unlock — surfaces groups that would take weeks to find manually.
"""

import asyncio
import re
import random
import httpx
from bs4 import BeautifulSoup
from config.search_terms import build_google_dork_queries, CITIES
from data.db import save_group

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

FB_GROUP_PATTERN = re.compile(r"facebook\.com/groups/([a-zA-Z0-9._-]+)")


def extract_fb_group_urls(html: str) -> list[str]:
    """Pull Facebook group URLs out of a search results page."""
    found = set()
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Google wraps URLs — unwrap them
        if "facebook.com/groups" in href:
            m = FB_GROUP_PATTERN.search(href)
            if m:
                group_id = m.group(1)
                if group_id not in ("feed", "discover", "create", "joins", "requests", "search"):
                    found.add(f"https://www.facebook.com/groups/{group_id}")

    # Also search raw text for any FB group URLs
    for m in FB_GROUP_PATTERN.finditer(html):
        group_id = m.group(1)
        if group_id not in ("feed", "discover", "create", "joins", "requests", "search"):
            found.add(f"https://www.facebook.com/groups/{group_id}")

    return list(found)


async def google_search(query: str, client: httpx.AsyncClient) -> list[str]:
    """Run a Google search and extract FB group URLs."""
    try:
        params = {"q": query, "num": 30, "hl": "en"}
        r = await client.get("https://www.google.com/search", params=params, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            return []  # Rate limited
        return extract_fb_group_urls(r.text)
    except Exception as e:
        print(f"  Google error for '{query}': {e}")
        return []


async def bing_search(query: str, client: httpx.AsyncClient) -> list[str]:
    """Run a Bing search — different index, unique results."""
    try:
        params = {"q": query, "count": 30}
        r = await client.get("https://www.bing.com/search", params=params, headers=HEADERS, timeout=15)
        return extract_fb_group_urls(r.text)
    except Exception as e:
        print(f"  Bing error for '{query}': {e}")
        return []


async def ddg_search(query: str, client: httpx.AsyncClient) -> list[str]:
    """DuckDuckGo — often surfaces groups the others miss."""
    try:
        params = {"q": query, "kl": "us-en"}
        r = await client.get("https://html.duckduckgo.com/html/", params=params, headers=HEADERS, timeout=15)
        return extract_fb_group_urls(r.text)
    except Exception as e:
        print(f"  DDG error for '{query}': {e}")
        return []


def infer_city_from_query(query: str) -> tuple[str, str]:
    """Try to figure out which city this query is about."""
    q_lower = query.lower()
    for city_data in CITIES:
        if city_data["city"].lower() in q_lower:
            return city_data["city"], city_data["state"]
    return "Auburn", "AL"


async def run_all_dorks(progress_callback=None) -> dict:
    """
    Run all Google/Bing/DDG dorks and save results to DB.
    Returns summary of what was found.
    """
    queries = build_google_dork_queries()
    all_urls: set[str] = set()
    new_saved = 0

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for i, q_data in enumerate(queries):
            query = q_data["query"]
            city = q_data.get("city", "Auburn")
            state = q_data.get("state", "AL")

            if progress_callback and i % 10 == 0:
                await progress_callback(f"Dorking [{i+1}/{len(queries)}]: {query[:60]}")

            # Hit all three engines per query
            results = []
            results += await google_search(query, client)
            await asyncio.sleep(random.uniform(2, 4))
            results += await bing_search(query, client)
            await asyncio.sleep(random.uniform(1, 3))
            results += await ddg_search(query, client)

            for url in results:
                if url not in all_urls:
                    all_urls.add(url)
                    group_id = url.rstrip("/").split("/")[-1]
                    group_name = f"Auburn Group — {group_id}"
                    await save_group(group_name, url, city, state)
                    new_saved += 1

            # Pause between query batches to avoid IP rate limits
            await asyncio.sleep(random.uniform(3, 6))

    return {
        "queries_run": len(queries),
        "unique_urls_found": len(all_urls),
        "saved_to_db": new_saved,
    }
