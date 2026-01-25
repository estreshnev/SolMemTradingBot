#!/usr/bin/env python3
"""
Setup Helius webhook for Pump.fun migration monitoring.

Usage:
    python scripts/setup_helius_webhook.py                      # List webhooks
    python scripts/setup_helius_webhook.py <webhook_url>        # Create webhook
    python scripts/setup_helius_webhook.py --delete <id>        # Delete webhook

Example:
    python scripts/setup_helius_webhook.py https://abc123.ngrok.io/webhook
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

HELIUS_API_KEY = os.getenv("BOT_HELIUS_API_KEY")

# Pump.fun program ID - monitors migrations to Raydium/PumpSwap
PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

HELIUS_API_BASE = "https://api.helius.xyz/v0"


async def create_webhook(webhook_url: str) -> dict:
    """Create a Helius webhook for Pump.fun migration events."""
    if not HELIUS_API_KEY:
        raise ValueError("BOT_HELIUS_API_KEY not set in .env")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{HELIUS_API_BASE}/webhooks",
            params={"api-key": HELIUS_API_KEY},
            json={
                "webhookURL": webhook_url,
                "transactionTypes": ["ANY"],
                "accountAddresses": [PUMP_FUN_PROGRAM],
                "webhookType": "enhanced",
            },
        )
        response.raise_for_status()
        return response.json()


async def list_webhooks() -> list:
    """List all existing webhooks."""
    if not HELIUS_API_KEY:
        raise ValueError("BOT_HELIUS_API_KEY not set in .env")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{HELIUS_API_BASE}/webhooks",
            params={"api-key": HELIUS_API_KEY},
        )
        response.raise_for_status()
        return response.json()


async def delete_webhook(webhook_id: str) -> None:
    """Delete a webhook by ID."""
    if not HELIUS_API_KEY:
        raise ValueError("BOT_HELIUS_API_KEY not set in .env")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{HELIUS_API_BASE}/webhooks/{webhook_id}",
            params={"api-key": HELIUS_API_KEY},
        )
        response.raise_for_status()


async def main() -> None:
    if len(sys.argv) < 2:
        # List existing webhooks
        print("Existing webhooks:")
        webhooks = await list_webhooks()
        for wh in webhooks:
            print(f"  ID: {wh.get('webhookID')}")
            print(f"  URL: {wh.get('webhookURL')}")
            print(f"  Type: {wh.get('webhookType')}")
            print(f"  Addresses: {wh.get('accountAddresses')}")
            print()

        if not webhooks:
            print("  (none)")
        print("\nUsage: python scripts/setup_helius_webhook.py <webhook_url>")
        print("       python scripts/setup_helius_webhook.py --delete <webhook_id>")
        return

    if sys.argv[1] == "--delete" and len(sys.argv) >= 3:
        webhook_id = sys.argv[2]
        await delete_webhook(webhook_id)
        print(f"Deleted webhook: {webhook_id}")
        return

    webhook_url = sys.argv[1]
    print(f"Creating webhook for Pump.fun migrations → {webhook_url}")
    print(f"  Pump.fun Program: {PUMP_FUN_PROGRAM}")

    result = await create_webhook(webhook_url)
    print(f"\nWebhook created!")
    print(f"  ID: {result.get('webhookID')}")
    print(f"  URL: {result.get('webhookURL')}")
    print(f"  Type: {result.get('webhookType')}")


if __name__ == "__main__":
    asyncio.run(main())