"""Event models for Pump.fun migration detection."""

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


class MigrationEvent(BaseModel):
    """Event emitted when a Pump.fun token migrates to Raydium/PumpSwap."""

    tx_signature: str
    timestamp: datetime = Field(default_factory=_utc_now)
    slot: int | None = None

    # Token info
    token_mint: str  # The migrated token address

    # Raw data for debugging
    raw_data: dict[str, Any] | None = Field(default=None, exclude=True)


class SignalEvent(BaseModel):
    """A filtered signal ready for notification."""

    token_mint: str
    tx_signature: str
    timestamp: datetime = Field(default_factory=_utc_now)

    # Dexscreener data
    dex: str  # "raydium" or "pumpswap"
    pair_address: str
    market_cap_usd: float
    volume_1h_usd: float
    age_minutes: float
    price_usd: float | None = None
    liquidity_usd: float | None = None

    # Links
    chart_url: str

    def format_message(self) -> str:
        """Format signal for logging/notification."""
        mc_str = f"${self.market_cap_usd:,.0f}"
        vol_str = f"${self.volume_1h_usd:,.0f}"
        age_str = f"{self.age_minutes:.1f}min"

        return (
            f"🚀 Migration Signal\n"
            f"Token: {self.token_mint[:8]}...{self.token_mint[-4:]}\n"
            f"DEX: {self.dex.upper()}\n"
            f"MC: {mc_str} | Vol(1h): {vol_str} | Age: {age_str}\n"
            f"Chart: {self.chart_url}"
        )