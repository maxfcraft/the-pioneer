"""
Reddit community finder — no login required, uses Reddit's public API.
Finds every Auburn-adjacent subreddit and relevant posts/threads.

Also searches city subreddits for Auburn-related posts (parents asking questions,
students sharing tips) — these are huge untapped audiences.
"""

import asyncio
import os
import httpx
from config.search_terms import REDDIT_TARGETS, CITIES

REDDIT_HEADERS = {
    "User-Agent": "AuburnBlueprintBot/1.0 (educational resource finder)",
}

AUBURN_KEYWORDS = [
    "auburn university", "auburn univ", "war eagle", "camp war eagle",
    "auburn freshman", "auburn orientation", "tiger transit",
    "auburn schedule", "auburn housing", "auburn football tickets",
    "going to auburn", "auburn next year", "auburn 2029",
]


async def search_subreddit(sub: str, keyword: str, client: httpx.AsyncClient) -> list[dict]:
    """Search a subreddit for Auburn-related posts."""
    results = []
    try:
        url = f"https://www.reddit.com/r/{sub}/search.json"
        params = {"q": keyword, "restrict_sr": 1, "sort": "new", "limit": 25}
        r = await client.get(url, params=params, headers=REDDIT_HEADERS, timeout=15)
        if r.status_code != 200:
            return []

        data = r.json()
        posts = data.get("data", {}).get("children", [])
        for post in posts:
            d = post.get("data", {})
            results.append({
                "subreddit": sub,
                "title": d.get("title", ""),
                "url": f"https://www.reddit.com{d.get('permalink', '')}",
                "author": d.get("author", ""),
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "created": d.get("created_utc", 0),
                "selftext": d.get("selftext", "")[:200],
            })
    except Exception as e:
        print(f"  Reddit error r/{sub} '{keyword}': {e}")

    return results


async def find_auburn_subreddits(client: httpx.AsyncClient) -> list[dict]:
    """Search Reddit itself for Auburn-related subreddits."""
    subs = []
    try:
        for term in ["auburn university", "war eagle auburn", "auburn alabama"]:
            r = await client.get(
                "https://www.reddit.com/subreddits/search.json",
                params={"q": term, "limit": 25},
                headers=REDDIT_HEADERS,
                timeout=15,
            )
            if r.status_code != 200:
                continue
            data = r.json()
            for item in data.get("data", {}).get("children", []):
                d = item.get("data", {})
                subs.append({
                    "name": d.get("display_name", ""),
                    "url": f"https://www.reddit.com/r/{d.get('display_name', '')}",
                    "title": d.get("title", ""),
                    "subscribers": d.get("subscribers", 0),
                    "description": d.get("public_description", "")[:200],
                    "type": "subreddit",
                })
            await asyncio.sleep(2)
    except Exception as e:
        print(f"  Subreddit search error: {e}")

    return subs


async def scan_city_subreddits(client: httpx.AsyncClient) -> list[dict]:
    """
    Check city subreddits for Auburn posts.
    Parents in r/Huntsville asking 'my kid is going to Auburn, any tips?' = perfect lead.
    """
    posts = []
    for city_data in CITIES:
        city = city_data["city"]
        # Common city subreddit patterns
        possible_subs = [city, f"{city}AL", f"{city}{city_data['state']}"]
        for sub in possible_subs:
            for keyword in ["auburn university", "auburn", "war eagle"]:
                results = await search_subreddit(sub, keyword, client)
                if results:
                    posts.extend(results)
                    break  # Found valid sub, move on
            await asyncio.sleep(1)

    return posts


async def run_reddit_scan() -> dict:
    """Full Reddit scan — returns structured data for export."""
    all_subreddits = []
    all_posts = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 1. Find Auburn-specific subreddits
        print("Finding Auburn subreddits...")
        discovered_subs = await find_auburn_subreddits(client)
        all_subreddits.extend(discovered_subs)

        # 2. Search known target subreddits
        print("Scanning target subreddits...")
        for target in REDDIT_TARGETS:
            sub = target["sub"]
            for keyword in AUBURN_KEYWORDS[:5]:  # Top 5 keywords per sub
                posts = await search_subreddit(sub, keyword, client)
                all_posts.extend(posts)
                await asyncio.sleep(1.5)  # Reddit rate limit: ~1 req/sec

        # 3. Scan city subreddits
        print("Scanning city subreddits...")
        city_posts = await scan_city_subreddits(client)
        all_posts.extend(city_posts)

    # Deduplicate posts by URL
    seen = set()
    unique_posts = []
    for post in all_posts:
        if post["url"] not in seen:
            seen.add(post["url"])
            unique_posts.append(post)

    # Deduplicate subreddits
    seen_subs = set()
    unique_subs = []
    for sub in all_subreddits:
        if sub["name"] not in seen_subs:
            seen_subs.add(sub["name"])
            unique_subs.append(sub)

    return {
        "subreddits": unique_subs,
        "posts": unique_posts,
        "total_subreddits": len(unique_subs),
        "total_posts": len(unique_posts),
    }
