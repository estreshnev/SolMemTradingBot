#!/usr/bin/env python3
"""
Setup Helius webhook for Raydium pool monitoring.

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

# Raydium program IDs
RAYDIUM_AMM_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_CLMM_PROGRAM = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"

HELIUS_API_BASE = "https://api.helius.xyz/v0"


async def create_webhook(webhook_url: str) -> dict:
    """Create a Helius webhook for Raydium pool events."""
    if not HELIUS_API_KEY:
        raise ValueError("BOT_HELIUS_API_KEY not set in .env")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{HELIUS_API_BASE}/webhooks",
            params={"api-key": HELIUS_API_KEY},
            json={
                "webhookURL": webhook_url,
                "transactionTypes": ["ANY"],
                "accountAddresses": [RAYDIUM_AMM_PROGRAM, RAYDIUM_CLMM_PROGRAM],
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
    print(f"Creating webhook for Raydium → {webhook_url}")
    print(f"  AMM Program: {RAYDIUM_AMM_PROGRAM}")
    print(f"  CLMM Program: {RAYDIUM_CLMM_PROGRAM}")

    result = await create_webhook(webhook_url)
    print(f"\nWebhook created!")
    print(f"  ID: {result.get('webhookID')}")
    print(f"  URL: {result.get('webhookURL')}")
    print(f"  Type: {result.get('webhookType')}")


if __name__ == "__main__":
    asyncio.run(main())