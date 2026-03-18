"""
Posts personalized messages to Auburn Facebook groups.
Each post is AI-generated and city-specific — sounds like a real student, not spam.
"""

import asyncio
import random
from playwright.async_api import Page
from facebook.browser import FacebookBrowser, human_delay, human_type
from data.db import get_unposted_groups, mark_group_posted, save_post
from ai.message_generator import generate_group_post
from config.cities import ALABAMA_CITIES


def get_city_data(city: str) -> dict:
    """Look up high school data for a city."""
    for c in ALABAMA_CITIES:
        if c["city"].lower() == city.lower():
            return c
    return {"city": city, "state": "AL", "high_schools": [], "search_terms": []}


async def post_to_group(page: Page, group_url: str, group_name: str, message: str) -> bool:
    """Navigate to a group and post a message."""
    try:
        await page.goto(group_url)
        await human_delay(3000, 5000)

        # Look for the "Write something..." post box
        # Facebook uses multiple selectors depending on group layout
        post_box_selectors = [
            "[data-testid='top-level-post-creator']",
            "div[role='button'][aria-label*='Write something']",
            "div[contenteditable='true']",
            "span[role='button']",
        ]

        clicked = False
        for selector in post_box_selectors:
            try:
                elem = await page.wait_for_selector(selector, timeout=5000)
                if elem:
                    await elem.click()
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            # Try clicking the placeholder text area
            try:
                await page.click("text=Write something")
                clicked = True
            except Exception:
                pass

        if not clicked:
            print(f"  Could not find post box in {group_name}")
            return False

        await human_delay(1000, 2000)

        # Type the message with human-like delays
        for char in message:
            await page.keyboard.type(char, delay=random.uniform(30, 100))
            # Occasional longer pause like a real person thinking
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.5, 1.5))

        await human_delay(1000, 2000)

        # Click Post button
        post_button_selectors = [
            "div[aria-label='Post']",
            "button[type='submit']",
            "div[role='button'] >> text=Post",
            "[data-testid='react-composer-post-button']",
        ]

        posted = False
        for selector in post_button_selectors:
            try:
                btn = await page.wait_for_selector(selector, timeout=5000)
                if btn:
                    await btn.click()
                    posted = True
                    break
            except Exception:
                continue

        if posted:
            await human_delay(3000, 6000)
            return True

        print(f"  Could not find post button in {group_name}")
        return False

    except Exception as e:
        print(f"  Error posting to {group_name}: {e}")
        return False


async def blast_unposted_groups(limit: int = 5) -> dict:
    """
    Post to unposted groups — pulls from database, generates personalized messages,
    posts with delays to avoid spam detection.
    Limit per run to stay under Facebook's radar.
    """
    groups = await get_unposted_groups(limit)
    if not groups:
        return {"posted": 0, "message": "No new groups to post to"}

    results = {"posted": 0, "failed": 0, "groups": []}

    async with FacebookBrowser() as fb:
        await fb.start(headless=True)

        logged_in = await fb.is_logged_in()
        if not logged_in:
            import os
            logged_in = await fb.login(os.getenv("FB_EMAIL"), os.getenv("FB_PASSWORD"))
            if not logged_in:
                return {"error": "Facebook login failed"}

        for group_id, group_name, group_url, city, state in groups:
            print(f"Posting to: {group_name} ({city})")

            # Get city data for personalization
            city_data = get_city_data(city)
            high_schools = city_data.get("high_schools", [])

            # Generate a fresh AI message for this specific city/group
            message = generate_group_post(city, state, high_schools, group_name)
            print(f"  Message preview: {message[:80]}...")

            success = await post_to_group(fb.page, group_url, group_name, message)

            if success:
                await mark_group_posted(group_id, message)
                await save_post(group_url, group_name, message)
                results["posted"] += 1
                results["groups"].append({"name": group_name, "city": city, "status": "posted"})
                print(f"  Posted successfully.")
            else:
                results["failed"] += 1
                results["groups"].append({"name": group_name, "city": city, "status": "failed"})

            # Wait 3-8 minutes between posts — Facebook rate limits hard
            if len(groups) > 1:
                wait = random.uniform(180, 480)
                print(f"  Waiting {wait:.0f}s before next post...")
                await asyncio.sleep(wait)

    return results
