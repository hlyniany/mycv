#!/usr/bin/env python3
"""
Find all Telegram groups/channels whose name contains the word "MASC"
(case-insensitive) and print their title and ID.

Usage:
    python find_masc_groups.py

Credentials are read from Azure Key Vault (tg-collector-kv).
Requires an active `az login` session.

Optional environment variables:
    TG_VAULT_NAME  — Key Vault name (default: tg-collector-kv)
    TG_SESSION     — path to .session file (default: /Users/vitaliy/Documents/GitHub/tg/collector)
    MASC_FILTER    — word to filter by (default: MASC)
"""

import asyncio
import os
import sys

from azure.identity import AzureCliCredential
from azure.keyvault.secrets import SecretClient
from telethon import TelegramClient
from telethon.tl.types import (
    Channel,
    Chat,
    ChatForbidden,
    ChannelForbidden,
)

DEFAULT_SESSION = "/Users/vitaliy/Documents/GitHub/tg/collector"
FILTER_WORD = os.environ.get("MASC_FILTER", "MASC")


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


async def find_groups(client: TelegramClient, keyword: str) -> list[dict]:
    keyword_lower = keyword.lower()
    results: list[dict] = []

    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        title  = dialog.name or ""

        if keyword_lower not in title.lower():
            continue

        if isinstance(entity, (ChatForbidden, ChannelForbidden)):
            results.append({
                "title":    title,
                "type":     "forbidden",
                "id":       entity.id,
                "username": "",
            })
        elif isinstance(entity, Chat):
            results.append({
                "title":    title,
                "type":     "group",
                "id":       entity.id,
                "username": "",
            })
        elif isinstance(entity, Channel):
            kind = "channel" if entity.broadcast else "supergroup"
            results.append({
                "title":    title,
                "type":     kind,
                "id":       entity.id,
                "username": entity.username or "",
            })

    return sorted(results, key=lambda d: d["title"].lower())


async def main() -> None:
    api_id, api_hash = get_credentials()
    session = os.environ.get("TG_SESSION", DEFAULT_SESSION)

    client = TelegramClient(session, api_id, api_hash)
    await client.start()

    try:
        print(f"Searching dialogs for '{FILTER_WORD}'…\n")
        groups = await find_groups(client, FILTER_WORD)

        if not groups:
            print(f"No groups/channels found containing '{FILTER_WORD}'.")
        else:
            print(f"Found {len(groups)} match(es):\n")
            print(f"{'Title':<50} {'Type':<12} {'ID':<15} {'Username'}")
            print("-" * 95)
            for g in groups:
                username = f"@{g['username']}" if g["username"] else "—"
                print(f"{g['title']:<50} {g['type']:<12} {g['id']:<15} {username}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
