"""Signal models for paper trading analysis."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SignalStatus(str, Enum):
    """Signal lifecycle status."""

    PENDING = "pending"  # Waiting for outcome data
    MIGRATED = "migrated"  # Token migrated to Raydium
    FAILED = "failed"  # Token rugged or never migrated
    EXPIRED = "expired"  # Too old, no longer tracking


class SignalOutcome(BaseModel):
    """Outcome data for a signal (filled over time)."""

    migrated: bool = False
    migration_time: datetime | None = None
    price_at_migration: Decimal | None = None

    # Simulated PnL assuming 75% sell pre-migration, 25% post
    simulated_entry_sol: Decimal | None = None
    simulated_exit_sol: Decimal | None = None
    simulated_pnl_pct: float | None = None
    simulated_pnl_sol: Decimal | None = None


class Signal(BaseModel):
    """A paper trading signal - captures what we would have bought."""

    id: str = Field(description="Unique signal ID (uuid)")
    token_address: str
    token_name: str | None = None
    token_symbol: str | None = None
    creator_address: str | None = None

    # Trigger event info
    trigger_tx_signature: str
    signal_time: datetime = Field(default_factory=_utc_now)

    # State at signal time (from filters)
    entry_curve_progress_pct: float
    entry_liquidity_sol: Decimal
    entry_market_cap_sol: Decimal | None = None
    entry_price_sol: Decimal | None = None  # Estimated token price in SOL

    # Additional context captured at signal time
    dev_holds_pct: float | None = None

    # Simulated trade params
    simulated_buy_sol: Decimal  # How much SOL we "would" spend

    # Status & outcome
    status: SignalStatus = SignalStatus.PENDING
    outcome: SignalOutcome = Field(default_factory=SignalOutcome)

    # Tracking
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    # Raw data for debugging
    raw_event: dict[str, Any] | None = Field(default=None, exclude=True)

    def calculate_simulated_pnl(
        self,
        exit_price_sol: Decimal,
        pre_migration_exit_pct: float = 0.75,
    ) -> None:
        """Calculate simulated PnL based on exit price.

        Strategy: sell pre_migration_exit_pct before migration, rest after.
        For simplicity, assume we exit at the given price for all.
        """
        if self.entry_price_sol is None or self.entry_price_sol == 0:
            return

        # Calculate tokens "bought"
        tokens_bought = self.simulated_buy_sol / self.entry_price_sol

        # Calculate exit value
        exit_value = tokens_bought * exit_price_sol

        self.outcome.simulated_entry_sol = self.simulated_buy_sol
        self.outcome.simulated_exit_sol = exit_value
        self.outcome.simulated_pnl_sol = exit_value - self.simulated_buy_sol

        if self.simulated_buy_sol > 0:
            self.outcome.simulated_pnl_pct = float(
                (exit_value - self.simulated_buy_sol) / self.simulated_buy_sol * 100
            )

        self.updated_at = _utc_now()