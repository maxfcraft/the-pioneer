"""
Searches Facebook for Auburn-related groups by city and saves them to the database.
Uses Facebook's group search — filters for public groups with Auburn/university content.
"""

import asyncio
import random
from playwright.async_api import Page
from facebook.browser import FacebookBrowser, human_delay
from data.db import save_group
from config.cities import ALABAMA_CITIES, FB_GROUP_SEARCH_TERMS


async def search_groups_for_term(page: Page, search_term: str, city: str, state: str) -> list[dict]:
    """Search Facebook groups for a specific term and return results."""
    groups = []

    encoded = search_term.replace(" ", "%20")
    url = f"https://www.facebook.com/search/groups/?q={encoded}"
    await page.goto(url)
    await human_delay(2000, 4000)

    # Scroll to load more results
    for _ in range(3):
        await page.keyboard.press("End")
        await human_delay(1000, 2000)

    # Extract group cards from search results
    try:
        group_links = await page.query_selector_all("a[href*='/groups/']")
        seen_urls = set()

        for link in group_links[:20]:  # Cap at 20 per search term
            try:
                href = await link.get_attribute("href")
                if not href or href in seen_urls:
                    continue
                if "/groups/feed" in href or "/groups/discover" in href:
                    continue

                # Clean the URL
                if "?" in href:
                    href = href.split("?")[0]
                if not href.startswith("http"):
                    href = "https://www.facebook.com" + href

                seen_urls.add(href)

                # Get the group name from nearby text
                parent = await link.evaluate_handle("el => el.closest('[role=\"article\"]') || el.parentElement")
                text = await page.evaluate("el => el ? el.innerText : ''", parent)
                group_name = text.split("\n")[0].strip()[:100] if text else search_term

                groups.append({
                    "name": group_name,
                    "url": href,
                    "city": city,
                    "state": state,
                })
            except Exception:
                continue
    except Exception as e:
        print(f"Error scraping groups for '{search_term}': {e}")

    return groups


async def find_groups_for_city(page: Page, city_data: dict) -> int:
    """Find all Auburn groups for a given city. Returns count of new groups found."""
    city = city_data["city"]
    state = city_data["state"]
    terms = city_data["search_terms"]
    found = 0

    for term in terms:
        print(f"  Searching: '{term}'")
        groups = await search_groups_for_term(page, term, city, state)
        for g in groups:
            await save_group(g["name"], g["url"], g["city"], g["state"])
            found += 1
        # Random delay between searches to avoid rate limiting
        await asyncio.sleep(random.uniform(3, 7))

    return found


async def find_all_auburn_groups() -> dict:
    """Main entry point — searches all cities and global Auburn terms."""
    results = {}

    async with FacebookBrowser() as fb:
        await fb.start(headless=True)

        logged_in = await fb.is_logged_in()
        if not logged_in:
            email = __import__("os").getenv("FB_EMAIL")
            password = __import__("os").getenv("FB_PASSWORD")
            logged_in = await fb.login(email, password)
            if not logged_in:
                return {"error": "Facebook login failed — check credentials or 2FA"}

        # Search by city
        for city_data in ALABAMA_CITIES:
            city = city_data["city"]
            print(f"Searching groups for {city}...")
            count = await find_groups_for_city(fb.page, city_data)
            results[city] = count
            await asyncio.sleep(random.uniform(5, 10))  # Pause between cities

        # Search global Auburn terms
        print("Searching global Auburn terms...")
        for term in FB_GROUP_SEARCH_TERMS:
            groups = await search_groups_for_term(fb.page, term, "Auburn", "AL")
            for g in groups:
                await save_group(g["name"], g["url"], g["city"], g["state"])
            results[f"global:{term[:30]}"] = len(groups)
            await asyncio.sleep(random.uniform(4, 8))

    return results
