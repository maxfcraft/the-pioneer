"""
Checks Facebook Messenger for new messages and auto-replies to move
people through the funnel toward buying Auburn Blueprint.
"""

import asyncio
import os
from playwright.async_api import Page
from facebook.browser import FacebookBrowser, human_delay
from ai.message_generator import generate_dm_response
from data.db import DB_PATH
import aiosqlite


async def get_conversation_stage(fb_user_id: str) -> int:
    """Get the funnel stage for a user (1=first contact, 2=follow-up, 3=final)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT stage FROM dm_conversations WHERE fb_user_id=?", (fb_user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 1


async def save_conversation(fb_user_id: str, fb_name: str, their_message: str, our_reply: str, stage: int):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await (await db.execute(
            "SELECT id FROM dm_conversations WHERE fb_user_id=?", (fb_user_id,)
        )).fetchone()

        if existing:
            await db.execute(
                """UPDATE dm_conversations
                   SET last_message=?, our_last_reply=?, stage=?, last_activity=CURRENT_TIMESTAMP
                   WHERE fb_user_id=?""",
                (their_message, our_reply, min(stage + 1, 3), fb_user_id),
            )
        else:
            await db.execute(
                """INSERT INTO dm_conversations
                   (fb_user_id, fb_user_name, last_message, our_last_reply, stage)
                   VALUES (?,?,?,?,?)""",
                (fb_user_id, fb_name, their_message, our_reply, 2),
            )
        await db.commit()


async def check_and_reply_to_messages(page: Page) -> list[dict]:
    """Check Messenger inbox and reply to unread messages."""
    replies_sent = []

    await page.goto("https://www.facebook.com/messages/t/")
    await human_delay(3000, 5000)

    # Look for unread conversations (bold text = unread)
    try:
        conversation_links = await page.query_selector_all("a[href*='/messages/t/']")

        for link in conversation_links[:10]:  # Check top 10
            try:
                href = await link.get_attribute("href")
                if not href:
                    continue

                # Extract user ID from URL
                user_id = href.split("/messages/t/")[-1].strip("/")

                await link.click()
                await human_delay(2000, 3000)

                # Get the last message text
                messages = await page.query_selector_all("div[dir='auto'] span")
                if not messages:
                    continue

                last_msg_elem = messages[-1]
                last_msg = await last_msg_elem.inner_text()

                if not last_msg or len(last_msg) < 3:
                    continue

                # Get user name
                name_elem = await page.query_selector("h2, [data-testid='conversation-name']")
                user_name = await name_elem.inner_text() if name_elem else user_id

                # Generate reply based on funnel stage
                stage = await get_conversation_stage(user_id)
                reply = generate_dm_response(last_msg, stage)

                # Type and send the reply
                input_box = await page.wait_for_selector(
                    "[contenteditable='true'][data-testid='mwc-composer-input']",
                    timeout=5000,
                )
                if input_box:
                    await input_box.click()
                    await page.keyboard.type(reply, delay=50)
                    await human_delay(500, 1000)
                    await page.keyboard.press("Enter")
                    await human_delay(1000, 2000)

                    await save_conversation(user_id, user_name, last_msg, reply, stage)
                    replies_sent.append({
                        "user": user_name,
                        "their_message": last_msg[:60],
                        "our_reply": reply[:60],
                        "stage": stage,
                    })

            except Exception as e:
                print(f"Error handling conversation: {e}")
                continue

    except Exception as e:
        print(f"Error checking messages: {e}")

    return replies_sent


async def run_dm_responder() -> dict:
    """Main entry point for the DM responder."""
    async with FacebookBrowser() as fb:
        await fb.start(headless=True)

        logged_in = await fb.is_logged_in()
        if not logged_in:
            logged_in = await fb.login(os.getenv("FB_EMAIL"), os.getenv("FB_PASSWORD"))
            if not logged_in:
                return {"error": "Facebook login failed"}

        replies = await check_and_reply_to_messages(fb.page)
        return {"replies_sent": len(replies), "details": replies}
