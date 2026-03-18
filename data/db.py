"""
SQLite database for tracking groups found, posts made, and DM conversations.
"""

import aiosqlite
import asyncio
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "auburn_blueprint.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups_found (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT,
                group_url TEXT UNIQUE,
                city TEXT,
                state TEXT,
                member_count TEXT,
                posted INTEGER DEFAULT 0,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts_made (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_url TEXT,
                group_name TEXT,
                message_used TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS dm_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fb_user_id TEXT,
                fb_user_name TEXT,
                last_message TEXT,
                our_last_reply TEXT,
                stage INTEGER DEFAULT 1,
                converted INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_url TEXT,
                title TEXT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1
            )
        """)
        await db.commit()


async def save_group(group_name: str, group_url: str, city: str, state: str, member_count: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO groups_found (group_name, group_url, city, state, member_count) VALUES (?,?,?,?,?)",
            (group_name, group_url, city, state, member_count),
        )
        await db.commit()


async def get_unposted_groups(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, group_name, group_url, city, state FROM groups_found WHERE posted=0 LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def mark_group_posted(group_id: int, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups_found SET posted=1 WHERE id=?", (group_id,))
        await db.commit()


async def save_post(group_url: str, group_name: str, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO posts_made (group_url, group_name, message_used) VALUES (?,?,?)",
            (group_url, group_name, message),
        )
        await db.commit()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        groups = await (await db.execute("SELECT COUNT(*) FROM groups_found")).fetchone()
        posted = await (await db.execute("SELECT COUNT(*) FROM groups_found WHERE posted=1")).fetchone()
        dms = await (await db.execute("SELECT COUNT(*) FROM dm_conversations")).fetchone()
        converted = await (await db.execute("SELECT COUNT(*) FROM dm_conversations WHERE converted=1")).fetchone()
        listings = await (await db.execute("SELECT COUNT(*) FROM marketplace_listings WHERE active=1")).fetchone()
        return {
            "groups_found": groups[0],
            "groups_posted": posted[0],
            "dm_conversations": dms[0],
            "converted": converted[0],
            "active_listings": listings[0],
        }
