"""
Playwright browser manager — handles Facebook login, session persistence,
and human-like behavior (random delays, mouse movement).
"""

import asyncio
import random
import os
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

SESSION_DIR = Path(__file__).parent.parent / "data" / "fb_session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


async def human_delay(min_ms: int = 800, max_ms: int = 2500):
    """Random delay to simulate human behavior."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def human_type(page: Page, selector: str, text: str):
    """Type text character by character with random delays."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char, delay=random.uniform(50, 150))


class FacebookBrowser:
    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def start(self, headless: bool = True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        # Use persistent context to save login session across runs
        self.context = await self.browser.new_context(
            storage_state=str(SESSION_DIR / "state.json") if (SESSION_DIR / "state.json").exists() else None,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        self.page = await self.context.new_page()
        return self

    async def save_session(self):
        """Save browser cookies/localStorage so we don't have to log in every time."""
        await self.context.storage_state(path=str(SESSION_DIR / "state.json"))

    async def login(self, email: str, password: str) -> bool:
        """Log into Facebook. Only needed once — session is saved after."""
        await self.page.goto("https://www.facebook.com/login")
        await human_delay(1000, 2000)

        # Check if already logged in
        if "facebook.com/login" not in self.page.url and "login" not in self.page.url:
            return True

        await human_type(self.page, "#email", email)
        await human_delay(500, 1000)
        await human_type(self.page, "#pass", password)
        await human_delay(300, 700)
        await self.page.click('[name="login"]')
        await human_delay(3000, 5000)

        # Check for 2FA or checkpoint
        if "checkpoint" in self.page.url or "two_step" in self.page.url:
            return False  # Signal that manual intervention needed

        if "facebook.com" in self.page.url and "login" not in self.page.url:
            await self.save_session()
            return True
        return False

    async def is_logged_in(self) -> bool:
        await self.page.goto("https://www.facebook.com")
        await human_delay(1500, 2500)
        return "login" not in self.page.url

    async def close(self):
        if self.context:
            await self.save_session()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
