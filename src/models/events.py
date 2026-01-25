from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class EventType(str, Enum):
    TOKEN_CREATED = "token_created"
    CURVE_PROGRESS = "curve_progress"
    MIGRATION = "migration"
    UNKNOWN = "unknown"


class BaseEvent(BaseModel):
    """Base event model - all events inherit from this."""

    event_type: EventType
    tx_signature: str
    timestamp: datetime = Field(default_factory=_utc_now)
    slot: int | None = None

    # Raw data for debugging/extensibility
    raw_data: dict[str, Any] | None = Field(default=None, exclude=True)


class TokenCreatedEvent(BaseEvent):
    """Emitted when a new token is created on Pump.fun."""

    event_type: EventType = EventType.TOKEN_CREATED
    token_address: str
    creator_address: str
    token_name: str | None = None
    token_symbol: str | None = None
    initial_liquidity_sol: float = 0.0


class CurveProgressEvent(BaseEvent):
    """Emitted on bonding curve progress updates."""

    event_type: EventType = EventType.CURVE_PROGRESS
    token_address: str
    curve_progress_pct: float
    liquidity_sol: float
    market_cap_sol: float | None = None
    token_price_sol: float | None = None  # Price per token in SOL
    token_amount: float | None = None  # Tokens transferred in this swap


class MigrationEvent(BaseEvent):
    """Emitted when token migrates from Pump.fun to Raydium."""

    event_type: EventType = EventType.MIGRATION
    token_address: str
    raydium_pool_address: str | None = None
    final_liquidity_sol: float = 0.0


class HeliusWebhookPayload(BaseModel):
    """Raw Helius webhook payload structure."""

    model_config = ConfigDict(populate_by_name=True)

    webhook_id: str | None = Field(default=None, alias="webhookID")
    transactions: list[dict[str, Any]] = Field(default_factory=list)
