from typing import Any

from src.models.events import (
    BaseEvent,
    CurveProgressEvent,
    EventType,
    MigrationEvent,
    TokenCreatedEvent,
)
from src.utils import get_logger

logger = get_logger(__name__)


class EventParser:
    """Parse raw Helius webhook transactions into structured events.

    This is a placeholder implementation. Real parsing logic will depend
    on actual Helius payload structure for Pump.fun events.
    """

    # Pump.fun program ID (mainnet)
    PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

    def parse_transaction(self, tx: dict[str, Any]) -> BaseEvent | None:
        """Parse a single transaction into an event, or None if not relevant."""
        try:
            signature = tx.get("signature", "")
            if not signature:
                return None

            # Extract event type from transaction
            event_type = self._detect_event_type(tx)
            if event_type == EventType.UNKNOWN:
                return None

            return self._build_event(event_type, tx)

        except Exception as e:
            logger.warning("failed_to_parse_transaction", error=str(e), tx_sig=tx.get("signature"))
            return None

    def _detect_event_type(self, tx: dict[str, Any]) -> EventType:
        """Detect event type from transaction data.

        TODO: Implement actual detection based on Helius payload structure.
        This requires analyzing real Pump.fun transaction patterns.
        """
        # Placeholder - will be implemented with real Helius data
        tx_type = tx.get("type", "")

        if "create" in tx_type.lower():
            return EventType.TOKEN_CREATED
        if "swap" in tx_type.lower() or "trade" in tx_type.lower():
            return EventType.CURVE_PROGRESS
        if "migrate" in tx_type.lower():
            return EventType.MIGRATION

        return EventType.UNKNOWN

    def _build_event(self, event_type: EventType, tx: dict[str, Any]) -> BaseEvent | None:
        """Build the appropriate event model from transaction data."""
        signature = tx.get("signature", "")
        slot = tx.get("slot")

        if event_type == EventType.TOKEN_CREATED:
            return TokenCreatedEvent(
                tx_signature=signature,
                slot=slot,
                token_address=tx.get("tokenAddress", ""),
                creator_address=tx.get("creator", ""),
                token_name=tx.get("tokenName"),
                token_symbol=tx.get("tokenSymbol"),
                initial_liquidity_sol=float(tx.get("initialLiquidity", 0)),
                raw_data=tx,
            )

        if event_type == EventType.CURVE_PROGRESS:
            return CurveProgressEvent(
                tx_signature=signature,
                slot=slot,
                token_address=tx.get("tokenAddress", ""),
                curve_progress_pct=float(tx.get("curveProgress", 0)),
                liquidity_sol=float(tx.get("liquidity", 0)),
                market_cap_sol=tx.get("marketCap"),
                raw_data=tx,
            )

        if event_type == EventType.MIGRATION:
            return MigrationEvent(
                tx_signature=signature,
                slot=slot,
                token_address=tx.get("tokenAddress", ""),
                raydium_pool_address=tx.get("poolAddress"),
                final_liquidity_sol=float(tx.get("finalLiquidity", 0)),
                raw_data=tx,
            )

        return None
