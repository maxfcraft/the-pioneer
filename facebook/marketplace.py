"""
Posts the Auburn Blueprint to Facebook Marketplace.
People search "Auburn University" on Marketplace and find your listing.
"""

import asyncio
import os
from playwright.async_api import Page
from facebook.browser import FacebookBrowser, human_delay, human_type
from ai.message_generator import generate_marketplace_description
from data.db import DB_PATH
import aiosqlite
from config.cities import MARKETPLACE_LISTING


async def post_marketplace_listing() -> dict:
    """Create a new Facebook Marketplace listing for Auburn Blueprint."""

    description = generate_marketplace_description()
    listing = MARKETPLACE_LISTING.copy()
    listing["description"] = description

    async with FacebookBrowser() as fb:
        await fb.start(headless=True)

        logged_in = await fb.is_logged_in()
        if not logged_in:
            logged_in = await fb.login(os.getenv("FB_EMAIL"), os.getenv("FB_PASSWORD"))
            if not logged_in:
                return {"error": "Facebook login failed"}

        page = fb.page

        # Navigate to Marketplace create listing
        await page.goto("https://www.facebook.com/marketplace/create/item")
        await human_delay(3000, 5000)

        try:
            # Select category — Education / Courses
            # Click "Choose a category"
            cat_selectors = [
                "[aria-label='Category']",
                "text=Choose a category",
                "select[name='category']",
            ]
            for sel in cat_selectors:
                try:
                    await page.click(sel, timeout=5000)
                    break
                except Exception:
                    continue

            await human_delay(1000, 2000)

            # Type listing title
            title_selectors = [
                "[placeholder='What are you selling?']",
                "[aria-label='Title']",
                "input[name='title']",
            ]
            for sel in title_selectors:
                try:
                    await human_type(page, sel, listing["title"])
                    break
                except Exception:
                    continue

            await human_delay(500, 1000)

            # Set price
            price_selectors = [
                "[placeholder='Price']",
                "[aria-label='Price']",
                "input[name='price']",
            ]
            for sel in price_selectors:
                try:
                    await human_type(page, sel, str(listing["price"]))
                    break
                except Exception:
                    continue

            await human_delay(500, 1000)

            # Write description
            desc_selectors = [
                "[placeholder='Describe your item']",
                "[aria-label='Description']",
                "textarea[name='description']",
            ]
            for sel in desc_selectors:
                try:
                    await page.click(sel, timeout=5000)
                    await page.keyboard.type(listing["description"], delay=30)
                    break
                except Exception:
                    continue

            await human_delay(1000, 2000)

            # Set location
            location_selectors = [
                "[placeholder='Location']",
                "[aria-label='Location']",
            ]
            for sel in location_selectors:
                try:
                    await human_type(page, sel, listing["location"])
                    await human_delay(1500, 2500)
                    # Select first autocomplete suggestion
                    await page.keyboard.press("ArrowDown")
                    await page.keyboard.press("Enter")
                    break
                except Exception:
                    continue

            await human_delay(1000, 2000)

            # Click Next/Publish
            publish_selectors = [
                "div[aria-label='Next']",
                "button >> text=Next",
                "div[role='button'] >> text=Publish",
            ]
            for sel in publish_selectors:
                try:
                    await page.click(sel, timeout=5000)
                    await human_delay(3000, 5000)
                    break
                except Exception:
                    continue

            # Try to publish if there's a second step
            for sel in ["div[aria-label='Publish']", "button >> text=Publish"]:
                try:
                    await page.click(sel, timeout=5000)
                    await human_delay(3000, 5000)
                    break
                except Exception:
                    continue

            listing_url = page.url

            # Save to DB
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "INSERT INTO marketplace_listings (listing_url, title) VALUES (?,?)",
                    (listing_url, listing["title"]),
                )
                await db.commit()

            return {"success": True, "url": listing_url, "title": listing["title"]}

        except Exception as e:
            return {"error": str(e)}
