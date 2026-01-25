"""Outcome tracker - updates signals with migration and price data."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog

from src.models.events import CurveProgressEvent, MigrationEvent
from src.signals.models import Signal, SignalStatus
from src.signals.storage import SignalStorage

logger = structlog.get_logger()


def _utc_now() -> datetime:
    return datetime.now(UTC)


class OutcomeTracker:
    """Tracks outcomes for pending signals and updates PnL calculations."""

    def __init__(
        self,
        storage: SignalStorage,
        expiry_hours: int = 24,
    ):
        self.storage = storage
        self.expiry_hours = expiry_hours

    def handle_migration(self, event: MigrationEvent) -> Signal | None:
        """Handle a migration event - update any pending signals for this token.

        Returns the updated signal if found, None otherwise.
        """
        log = logger.bind(token=event.token_address, event_type="migration")

        signals = self.storage.get_by_token(event.token_address)
        pending_signals = [s for s in signals if s.status == SignalStatus.PENDING]

        if not pending_signals:
            log.debug("migration_no_pending_signals")
            return None

        # Update the most recent pending signal
        signal = pending_signals[0]
        signal.status = SignalStatus.MIGRATED
        signal.outcome.migrated = True
        signal.outcome.migration_time = event.timestamp
        signal.outcome.price_at_migration = Decimal(str(event.final_liquidity_sol))
        signal.updated_at = _utc_now()

        # Note: Cannot calculate PnL at migration without actual price data
        # Migration event only has liquidity, not token price
        # PnL calculation requires RPC query for actual price (not implemented)

        self.storage.save(signal)

        log.info(
            "signal_migration_recorded",
            signal_id=signal.id,
            pnl_pct=signal.outcome.simulated_pnl_pct,
        )

        return signal

    def handle_curve_update(self, event: CurveProgressEvent) -> list[Signal]:
        """Handle curve progress updates for pending signals.

        Can be used to track price movements for signals before migration.
        Returns list of updated signals.
        """
        log = logger.bind(token=event.token_address)

        signals = self.storage.get_by_token(event.token_address)
        pending_signals = [s for s in signals if s.status == SignalStatus.PENDING]

        if not pending_signals:
            return []

        updated = []
        # Only use actual price from swap data, no estimates
        current_price = (
            Decimal(str(event.token_price_sol))
            if event.token_price_sol and event.token_price_sol > 0
            else None
        )

        for signal in pending_signals:
            if current_price is not None and signal.entry_price_sol:
                # Track unrealized PnL
                signal.calculate_simulated_pnl(current_price)
                signal.updated_at = _utc_now()
                self.storage.save(signal)
                updated.append(signal)

                log.debug(
                    "signal_price_updated",
                    signal_id=signal.id,
                    unrealized_pnl_pct=signal.outcome.simulated_pnl_pct,
                )

        return updated

    def expire_old_signals(self) -> int:
        """Mark old pending signals as expired.

        Returns count of expired signals.
        """
        cutoff = _utc_now() - timedelta(hours=self.expiry_hours)
        pending = self.storage.get_pending(limit=1000)

        expired_count = 0
        for signal in pending:
            if signal.signal_time < cutoff:
                signal.status = SignalStatus.EXPIRED
                signal.updated_at = _utc_now()
                self.storage.save(signal)
                expired_count += 1

                logger.debug(
                    "signal_expired",
                    signal_id=signal.id,
                    token=signal.token_address,
                    age_hours=(_utc_now() - signal.signal_time).total_seconds() / 3600,
                )

        if expired_count:
            logger.info("signals_expired", count=expired_count)

        return expired_count

    def mark_failed(self, token_address: str, reason: str = "rugged") -> list[Signal]:
        """Mark all pending signals for a token as failed (rugged, etc).

        Returns list of updated signals.
        """
        signals = self.storage.get_by_token(token_address)
        pending_signals = [s for s in signals if s.status == SignalStatus.PENDING]

        for signal in pending_signals:
            signal.status = SignalStatus.FAILED
            signal.updated_at = _utc_now()
            # Set PnL to -100% for rugs
            signal.outcome.simulated_pnl_pct = -100.0
            signal.outcome.simulated_pnl_sol = -signal.simulated_buy_sol
            self.storage.save(signal)

            logger.info(
                "signal_marked_failed",
                signal_id=signal.id,
                token=token_address,
                reason=reason,
            )

        return pending_signals