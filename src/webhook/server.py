"""FastAPI webhook server for Raydium pool detection."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.config import Settings, get_settings
from src.models.events import HeliusWebhookPayload
from src.utils import get_logger, setup_logging
from src.webhook.idempotency import IdempotencyStore

logger = get_logger(__name__)

# Raydium program IDs for detection
RAYDIUM_AMM_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_CLMM_PROGRAM = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"


class WebhookHandler:
    """Handles incoming Helius webhooks for Raydium pool detection."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.seen_signatures: IdempotencyStore[bool] = IdempotencyStore(max_size=10000)

    async def handle(self, payload: HeliusWebhookPayload) -> dict[str, Any]:
        """Process webhook payload and return summary."""
        processed = 0
        duplicates = 0
        pools_detected = 0

        for tx in payload.transactions:
            sig = tx.get("signature", "")

            # Idempotency check
            if self.seen_signatures.contains(sig):
                duplicates += 1
                logger.debug("duplicate_transaction", tx_sig=sig)
                continue

            # Mark as seen
            self.seen_signatures.add(sig, True)

            # Log transaction for analysis
            logger.info(
                "transaction_received",
                tx_sig=sig,
                tx_type=tx.get("type"),
                source=tx.get("source"),
            )

            # TODO: Parse Raydium pool creation events
            # TODO: Extract pool info (base_token, quote_token, liquidity)
            # TODO: Enrich with Dexscreener data
            # TODO: Filter and send to Telegram

            processed += 1

        return {
            "status": "ok",
            "processed": processed,
            "duplicates": duplicates,
            "pools_detected": pools_detected,
        }


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application with dependency injection."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        setup_logging(log_level=settings.log_level, json_format=True)
        logger.info(
            "server_starting",
            mode=settings.mode.value,
            host=settings.webhook.host,
            port=settings.webhook.port,
        )
        yield
        logger.info("server_stopping")

    app = FastAPI(
        title="Raydium Signal Bot",
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

            # Helius sends a list of transactions directly, not wrapped in a dict
            # Normalize to our expected format
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