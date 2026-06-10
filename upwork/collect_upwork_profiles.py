#!/usr/bin/env python3
"""
Parse messages from specified Telegram groups and extract Upwork profile URLs
matching https://www.upwork.com/freelancers/* — save them to SQLite.

Usage:
    python3 collect_upwork_profiles.py

Credentials are read from Azure Key Vault (tg-collector-kv).
Requires an active `az login` session.

Optional environment variables:
    TG_VAULT_NAME  — Key Vault name (default: tg-collector-kv)
    TG_SESSION     — path to .session file
                     (default: /Users/vitaliy/Documents/GitHub/tg/collector)
    DB_PATH        — SQLite database path (default: upwork_profiles.db)
"""

import asyncio
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient
from telethon import TelegramClient

# ── Config ─────────────────────────────────────────────────────────────────────

GROUP_IDS = [1389655960, 1839534039]

UPWORK_RE = re.compile(
    r"https?://(?:www\.)?upwork\.com/freelancers/[^\s\"'<>)]+",
    re.IGNORECASE,
)

DEFAULT_SESSION = "/Users/vitaliy/Documents/GitHub/tg/collector"
DB_PATH = os.environ.get("DB_PATH", "upwork_profiles.db")

# ── Azure Key Vault credentials ────────────────────────────────────────────────

def get_credentials() -> tuple[int, str]:
    vault_name = os.environ.get("TG_VAULT_NAME", "tg-collector-kv")
    try:
        kv = SecretClient(
            vault_url=f"https://{vault_name}.vault.azure.net",
            credential=AzureCliCredential(),
        )
        api_id   = int(kv.get_secret("TG-API-ID").value)
        api_hash = kv.get_secret("TG-API-HASH").value
    except Exception as exc:
        sys.exit(f"Key Vault error: {exc}\nRun 'az login' first.")
    return api_id, api_hash

# ── SQLite ─────────────────────────────────────────────────────────────────────

def init_db(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS upwork_profiles (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            url           TEXT    NOT NULL UNIQUE,
            group_id      INTEGER NOT NULL,
            group_title   TEXT,
            message_id    INTEGER,
            sender_id     INTEGER,
            message_date  TEXT,
            message_text  TEXT,
            added_at      TEXT    NOT NULL
        )
    """)
    con.commit()
    return con


def upsert_profile(
    con: sqlite3.Connection,
    url: str,
    group_id: int,
    group_title: str,
    message_id: int,
    sender_id: int | None,
    message_date: datetime | None,
    message_text: str,
) -> bool:
    """Insert profile URL. Returns True if new, False if already existed."""
    try:
        con.execute(
            """
            INSERT INTO upwork_profiles
                (url, group_id, group_title, message_id, sender_id,
                 message_date, message_text, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url,
                group_id,
                group_title,
                message_id,
                sender_id,
                message_date.isoformat() if message_date else None,
                message_text[:1000],
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        # URL already in DB (UNIQUE constraint)
        return False

# ── Telegram scraping ──────────────────────────────────────────────────────────

def extract_urls_from_message(msg) -> list[str]:
    """Extract Upwork URLs from message text and web-preview entities."""
    urls: list[str] = []

    # Plain text
    text = getattr(msg, "text", "") or getattr(msg, "message", "") or ""
    urls.extend(UPWORK_RE.findall(text))

    # Inline URL entities (MessageEntityTextUrl)
    for entity in getattr(msg, "entities", None) or []:
        href = getattr(entity, "url", None)
        if href and UPWORK_RE.match(href):
            urls.append(href)

    # Web preview
    media = getattr(msg, "media", None)
    if media:
        webpage = getattr(media, "webpage", None)
        if webpage:
            page_url = getattr(webpage, "url", None)
            if page_url and UPWORK_RE.match(page_url):
                urls.append(page_url)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        # Normalise: strip trailing punctuation that regex may have caught
        u = u.rstrip(".,;:!?)")
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


async def scrape_group(
    client: TelegramClient,
    con: sqlite3.Connection,
    group_id: int,
) -> None:
    try:
        entity = await client.get_entity(group_id)
    except Exception as exc:
        print(f"  [!] Cannot get entity {group_id}: {exc}")
        return

    group_title = getattr(entity, "title", str(group_id))
    print(f"\n── Group: {group_title} (ID {group_id}) ──")

    new_count = 0
    total_messages = 0

    async for msg in client.iter_messages(entity, limit=None):
        total_messages += 1
        if total_messages % 1000 == 0:
            print(f"  … scanned {total_messages} messages, {new_count} new profiles so far")

        urls = extract_urls_from_message(msg)
        for url in urls:
            text = getattr(msg, "text", "") or getattr(msg, "message", "") or ""
            sender_id = None
            if msg.sender_id:
                sender_id = msg.sender_id
            is_new = upsert_profile(
                con,
                url=url,
                group_id=group_id,
                group_title=group_title,
                message_id=msg.id,
                sender_id=sender_id,
                message_date=msg.date,
                message_text=text,
            )
            status = "NEW" if is_new else "dup"
            if is_new:
                new_count += 1
            print(f"  [{status}] {url}")

    print(f"  Done. Scanned {total_messages} messages, added {new_count} new profile(s).")


async def main() -> None:
    api_id, api_hash = get_credentials()
    session = os.environ.get("TG_SESSION", DEFAULT_SESSION)

    con = init_db(DB_PATH)
    print(f"Database: {DB_PATH}")

    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    try:
        for group_id in GROUP_IDS:
            await scrape_group(client, con, group_id)
    finally:
        await client.disconnect()
        con.close()

    print(f"\nAll done. Results saved to {DB_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
