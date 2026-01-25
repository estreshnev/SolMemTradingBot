"""Parse Helius webhook transactions into structured events."""

import contextlib
from datetime import datetime
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

    Helius enhanced transaction format:
    - type: SWAP, CREATE, UNKNOWN, WITHDRAW, etc.
    - source: PUMP_FUN for Pump.fun transactions
    - signature: transaction signature
    - slot: slot number
    - timestamp: unix timestamp
    - tokenTransfers: list of token transfers
    - nativeTransfers: list of SOL transfers
    - accountData: account balance changes
    """

    # Pump.fun program ID (mainnet)
    PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

    # Pump.fun token suffix
    PUMP_TOKEN_SUFFIX = "pump"

    def parse_transaction(self, tx: dict[str, Any]) -> BaseEvent | None:
        """Parse a single transaction into an event, or None if not relevant."""
        try:
            signature = tx.get("signature", "")
            if not signature:
                return None

            # Only process Pump.fun transactions
            source = tx.get("source", "")
            if source != "PUMP_FUN":
                return None

            # Extract event type from transaction
            event_type = self._detect_event_type(tx)
            if event_type == EventType.UNKNOWN:
                return None

            return self._build_event(event_type, tx)

        except Exception as e:
            logger.warning(
                "failed_to_parse_transaction",
                error=str(e),
                tx_sig=tx.get("signature"),
            )
            return None

    def _detect_event_type(self, tx: dict[str, Any]) -> EventType:
        """Detect event type from Helius transaction type field."""
        tx_type = tx.get("type", "").upper()

        if tx_type == "CREATE":
            return EventType.TOKEN_CREATED
        if tx_type == "SWAP":
            return EventType.CURVE_PROGRESS
        # Helius may use different type for migrations
        if tx_type in ("MIGRATE", "MIGRATION"):
            return EventType.MIGRATION

        return EventType.UNKNOWN

    def _build_event(self, event_type: EventType, tx: dict[str, Any]) -> BaseEvent | None:
        """Build the appropriate event model from transaction data."""
        signature = tx.get("signature", "")
        slot = tx.get("slot")

        # Parse timestamp
        timestamp = None
        if tx.get("timestamp"):
            with contextlib.suppress(ValueError, TypeError):
                timestamp = datetime.fromtimestamp(tx["timestamp"])

        if event_type == EventType.TOKEN_CREATED:
            return self._build_token_created(tx, signature, slot, timestamp)

        if event_type == EventType.CURVE_PROGRESS:
            return self._build_curve_progress(tx, signature, slot, timestamp)

        if event_type == EventType.MIGRATION:
            return self._build_migration(tx, signature, slot, timestamp)

        return None

    def _build_token_created(
        self,
        tx: dict[str, Any],
        signature: str,
        slot: int | None,
        timestamp: datetime | None,
    ) -> TokenCreatedEvent | None:
        """Build TokenCreatedEvent from CREATE transaction."""
        # Extract token info from tokenTransfers or description
        token_transfers = tx.get("tokenTransfers", [])
        token_address = ""
        creator_address = tx.get("feePayer", "")

        # Find the pump.fun token in transfers
        for transfer in token_transfers:
            mint = transfer.get("mint", "")
            if mint.endswith(self.PUMP_TOKEN_SUFFIX):
                token_address = mint
                break

        if not token_address:
            # Try to extract from account data
            for acc in tx.get("accountData", []):
                for tbc in acc.get("tokenBalanceChanges", []):
                    mint = tbc.get("mint", "")
                    if mint.endswith(self.PUMP_TOKEN_SUFFIX):
                        token_address = mint
                        break

        if not token_address:
            logger.debug("create_event_no_token", tx_sig=signature)
            return None

        # Calculate initial liquidity from native transfers
        initial_liquidity = 0.0
        for transfer in tx.get("nativeTransfers", []):
            amount = transfer.get("amount", 0)
            if amount > 0:
                initial_liquidity += amount / 1e9  # lamports to SOL

        event = TokenCreatedEvent(
            tx_signature=signature,
            slot=slot,
            token_address=token_address,
            creator_address=creator_address,
            initial_liquidity_sol=initial_liquidity,
            raw_data=tx,
        )
        if timestamp:
            event.timestamp = timestamp

        return event

    def _build_curve_progress(
        self,
        tx: dict[str, Any],
        signature: str,
        slot: int | None,
        timestamp: datetime | None,
    ) -> CurveProgressEvent | None:
        """Build CurveProgressEvent from SWAP transaction."""
        # Extract token and amounts from transfers
        token_transfers = tx.get("tokenTransfers", [])
        native_transfers = tx.get("nativeTransfers", [])

        token_address = ""
        token_amount = 0.0

        # Find pump.fun token and amount
        for transfer in token_transfers:
            mint = transfer.get("mint", "")
            if mint.endswith(self.PUMP_TOKEN_SUFFIX):
                token_address = mint
                token_amount = abs(float(transfer.get("tokenAmount", 0)))
                break

        if not token_address:
            # Try accountData
            for acc in tx.get("accountData", []):
                for tbc in acc.get("tokenBalanceChanges", []):
                    mint = tbc.get("mint", "")
                    if mint.endswith(self.PUMP_TOKEN_SUFFIX):
                        token_address = mint
                        # Get token amount from raw amount
                        raw = tbc.get("rawTokenAmount", {})
                        decimals = raw.get("decimals", 6)
                        amount = abs(int(raw.get("tokenAmount", 0)))
                        token_amount = amount / (10**decimals)
                        break

        if not token_address:
            return None

        # Find the main SOL amount from nativeTransfers or accountData
        sol_amounts = [abs(t.get("amount", 0)) for t in native_transfers]

        # Fallback: get SOL from accountData.nativeBalanceChange if nativeTransfers empty
        if not sol_amounts:
            for acc in tx.get("accountData", []):
                change = acc.get("nativeBalanceChange", 0)
                if change != 0:
                    sol_amounts.append(abs(change))

        main_sol_amount = max(sol_amounts) / 1e9 if sol_amounts else 0.0
        total_sol = sum(abs(x) for x in sol_amounts) / 1e9 / 2  # Divide by 2 to avoid double counting

        # Calculate price: SOL per token
        token_price = None
        market_cap = None
        if token_amount > 0 and main_sol_amount > 0:
            token_price = main_sol_amount / token_amount
            # Pump.fun tokens have 1B total supply
            market_cap = token_price * 1_000_000_000

        event = CurveProgressEvent(
            tx_signature=signature,
            slot=slot,
            token_address=token_address,
            curve_progress_pct=0.0,  # Would need RPC call to get actual progress
            liquidity_sol=total_sol,
            market_cap_sol=market_cap,
            token_price_sol=token_price,
            token_amount=token_amount,
            raw_data=tx,
        )
        if timestamp:
            event.timestamp = timestamp

        return event

    def _build_migration(
        self,
        tx: dict[str, Any],
        signature: str,
        slot: int | None,
        timestamp: datetime | None,
    ) -> MigrationEvent | None:
        """Build MigrationEvent from MIGRATE transaction."""
        token_transfers = tx.get("tokenTransfers", [])
        token_address = ""

        for transfer in token_transfers:
            mint = transfer.get("mint", "")
            if mint.endswith(self.PUMP_TOKEN_SUFFIX):
                token_address = mint
                break

        if not token_address:
            return None

        # Extract final liquidity
        final_liquidity = 0.0
        for transfer in tx.get("nativeTransfers", []):
            amount = abs(transfer.get("amount", 0))
            final_liquidity += amount / 1e9

        event = MigrationEvent(
            tx_signature=signature,
            slot=slot,
            token_address=token_address,
            final_liquidity_sol=final_liquidity,
            raw_data=tx,
        )
        if timestamp:
            event.timestamp = timestamp

        return event