"""Event models for Raydium pool detection."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class HeliusWebhookPayload(BaseModel):
    """Raw Helius webhook payload structure."""

    model_config = ConfigDict(populate_by_name=True)

    webhook_id: str | None = Field(default=None, alias="webhookID")
    transactions: list[dict[str, Any]] = Field(default_factory=list)


class RaydiumPoolCreated(BaseModel):
    """Event emitted when a new Raydium pool is created."""

    tx_signature: str
    timestamp: datetime = Field(default_factory=_utc_now)
    slot: int | None = None

    # Pool info
    pool_address: str
    base_token: str  # The memecoin
    quote_token: str  # Usually SOL or USDC
    initial_liquidity_base: float | None = None
    initial_liquidity_quote: float | None = None

    # Raw data for debugging
    raw_data: dict[str, Any] | None = Field(default=None, exclude=True)