"""FastAPI webhook server for Pump.fun migration detection."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.config import Settings, get_settings
from src.enrichment import DexscreenerClient
from src.models.events import HeliusWebhookPayload, MigrationEvent, SignalEvent
from src.utils import get_logger, setup_logging
from src.webhook.idempotency import IdempotencyStore

logger = get_logger(__name__)

# Pump.fun program ID
PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"


class MigrationParser:
    """Parse Pump.fun migration events from Helius transactions."""

    @staticmethod
    def parse(tx: dict[str, Any]) -> MigrationEvent | None:
        """Extract migration event from transaction.

        Pump.fun migrations have source=PUMP_FUN and involve token transfers
        to Raydium or PumpSwap pools.
        """
        source = tx.get("source", "")
        tx_type = tx.get("type", "")
        signature = tx.get("signature", "")

        # Must be from Pump.fun
        if source != "PUMP_FUN":
            return None

        # Look for token mint in the transaction
        token_mint = MigrationParser._extract_token_mint(tx)
        if not token_mint:
            return None

        # Check if this looks like a migration (has LP-related activity)
        if not MigrationParser._is_migration(tx):
            return None

        return MigrationEvent(
            tx_signature=signature,
            slot=tx.get("slot"),
            token_mint=token_mint,
            raw_data=tx,
        )

    @staticmethod
    def _extract_token_mint(tx: dict[str, Any]) -> str | None:
        """Extract the memecoin mint address from transaction."""
        # Check token transfers
        token_transfers = tx.get("tokenTransfers") or []
        for transfer in token_transfers:
            mint = transfer.get("mint", "")
            # Skip common tokens (SOL wrapped, USDC, etc.)
            if mint and not MigrationParser._is_common_token(mint):
                return mint

        # Check account data for token mints
        account_data = tx.get("accountData") or []
        for account in account_data:
            if account.get("tokenBalanceChanges"):
                for change in account["tokenBalanceChanges"]:
                    mint = change.get("mint", "")
                    if mint and not MigrationParser._is_common_token(mint):
                        return mint

        return None

    @staticmethod
    def _is_migration(tx: dict[str, Any]) -> bool:
        """Check if transaction appears to be a migration.

        Look for signs of liquidity pool creation:
        - Multiple token transfers
        - Interactions with Raydium/PumpSwap programs
        - LP token minting
        """
        # Check for Raydium or pool-related instructions
        instructions = tx.get("instructions") or []
        account_keys = tx.get("accountKeys") or []

        # Known pool/DEX program IDs
        pool_programs = {
            "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM
            "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK",  # Raydium CLMM
            "pSwpGyAJiLMTUidSTPXhNFyJz3aLH41mGqhW3s1hkLd",  # PumpSwap
        }

        # Check if any pool programs are involved
        for key in account_keys:
            if isinstance(key, dict):
                pubkey = key.get("pubkey", "")
            else:
                pubkey = str(key)
            if pubkey in pool_programs:
                return True

        # Check instructions for pool programs
        for inst in instructions:
            program_id = inst.get("programId", "")
            if program_id in pool_programs:
                return True

        # Also check for significant token movement (migration sign)
        token_transfers = tx.get("tokenTransfers") or []
        if len(token_transfers) >= 2:
            return True

        return False

    @staticmethod
    def _is_common_token(mint: str) -> bool:
        """Check if mint is a common token (SOL, USDC, etc.)."""
        common_tokens = {
            "So11111111111111111111111111111111111111112",  # Wrapped SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        }
        return mint in common_tokens


class WebhookHandler:
    """Handles incoming Helius webhooks for migration detection."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.seen_signatures: IdempotencyStore[bool] = IdempotencyStore(max_size=10000)
        self.dexscreener = DexscreenerClient(settings)
        self.parser = MigrationParser()

    async def handle(self, payload: HeliusWebhookPayload) -> dict[str, Any]:
        """Process webhook payload and return summary."""
        processed = 0
        duplicates = 0
        migrations_detected = 0
        signals_generated = 0

        for tx in payload.transactions:
            sig = tx.get("signature", "")

            # Idempotency check
            if self.seen_signatures.contains(sig):
                duplicates += 1
                logger.debug("duplicate_transaction", tx_sig=sig)
                continue

            # Mark as seen
            self.seen_signatures.add(sig, True)
            processed += 1

            # Try to parse as migration
            migration = self.parser.parse(tx)
            if not migration:
                continue

            migrations_detected += 1
            logger.info(
                "migration_detected",
                tx_sig=sig,
                token_mint=migration.token_mint,
            )

            # Process migration and generate signal if filters pass
            signal = await self._process_migration(migration)
            if signal:
                signals_generated += 1

        return {
            "status": "ok",
            "processed": processed,
            "duplicates": duplicates,
            "migrations_detected": migrations_detected,
            "signals_generated": signals_generated,
        }

    async def _process_migration(self, migration: MigrationEvent) -> SignalEvent | None:
        """Process migration: fetch Dexscreener data, apply filters, log signal."""
        # Fetch pair data from Dexscreener
        pair = await self.dexscreener.get_raydium_or_pumpswap_pair(migration.token_mint)

        if not pair:
            logger.info(
                "no_dex_pair_found",
                token_mint=migration.token_mint,
            )
            return None

        # Check required data exists
        if pair.market_cap_usd is None or pair.volume_1h_usd is None or pair.age_minutes is None:
            logger.info(
                "incomplete_pair_data",
                token_mint=migration.token_mint,
                mc=pair.market_cap_usd,
                vol_1h=pair.volume_1h_usd,
                age=pair.age_minutes,
            )
            return None

        # Apply filters
        filters = self.settings.filters

        if pair.market_cap_usd < filters.min_market_cap_usd:
            logger.debug(
                "filter_rejected_mc",
                token_mint=migration.token_mint,
                mc=pair.market_cap_usd,
                min_mc=filters.min_market_cap_usd,
            )
            return None

        if pair.volume_1h_usd < filters.min_volume_1h_usd:
            logger.debug(
                "filter_rejected_volume",
                token_mint=migration.token_mint,
                vol_1h=pair.volume_1h_usd,
                min_vol=filters.min_volume_1h_usd,
            )
            return None

        if pair.age_minutes > filters.max_age_minutes:
            logger.debug(
                "filter_rejected_age",
                token_mint=migration.token_mint,
                age=pair.age_minutes,
                max_age=filters.max_age_minutes,
            )
            return None

        # All filters passed - create signal
        signal = SignalEvent(
            token_mint=migration.token_mint,
            tx_signature=migration.tx_signature,
            dex=pair.dex_id,
            pair_address=pair.pair_address,
            market_cap_usd=pair.market_cap_usd,
            volume_1h_usd=pair.volume_1h_usd,
            age_minutes=pair.age_minutes,
            price_usd=pair.price_usd,
            liquidity_usd=pair.liquidity_usd,
            chart_url=pair.chart_url,
        )

        # Log the signal
        logger.info(
            "signal_generated",
            token_mint=signal.token_mint,
            dex=signal.dex,
            mc=signal.market_cap_usd,
            vol_1h=signal.volume_1h_usd,
            age_min=signal.age_minutes,
            chart=signal.chart_url,
        )

        # Print formatted message to console
        print("\n" + "=" * 50)
        print(signal.format_message())
        print("=" * 50 + "\n")

        return signal


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application with dependency injection."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setup_logging(log_level=settings.log_level, json_format=True)
        logger.info(
            "server_starting",
            mode=settings.mode.value,
            filters=settings.filters.model_dump(),
        )
        yield
        logger.info("server_stopping")

    app = FastAPI(
        title="Solana Memecoin Signal Bot",
        version="0.1.0",
        lifespan=lifespan,
    )

    handler = WebhookHandler(settings)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy", "mode": settings.mode.value}

    @app.post("/webhook")
    async def webhook(request: Request) -> JSONResponse:
        try:
            raw_body = await request.json()

            # Log raw payload for analysis (debug mode)
            if settings.log_level.upper() == "DEBUG":
                logger.debug("raw_webhook_payload", payload=raw_body)

            # Helius sends a list of transactions directly
            if isinstance(raw_body, list):
                raw_body = {"transactions": raw_body}

            payload = HeliusWebhookPayload.model_validate(raw_body)
            result = await handler.handle(payload)
            return JSONResponse(content=result, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("webhook_error", error=str(e))
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @app.post("/webhook/debug")
    async def webhook_debug(request: Request) -> JSONResponse:
        """Debug endpoint - logs full payload and returns it."""
        raw_body = await request.json()
        logger.info("debug_webhook_payload", payload=raw_body)
        return JSONResponse(content={"received": raw_body}, status_code=status.HTTP_200_OK)

    return app


# Default app instance for uvicorn
app = create_app()