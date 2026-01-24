from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.config import Settings, get_settings
from src.models.events import HeliusWebhookPayload
from src.utils import get_logger, setup_logging
from src.webhook.idempotency import IdempotencyStore
from src.webhook.parser import EventParser

logger = get_logger(__name__)


class WebhookHandler:
    """Handles incoming Helius webhooks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.parser = EventParser()
        self.seen_signatures: IdempotencyStore[bool] = IdempotencyStore(max_size=10000)

    async def handle(self, payload: HeliusWebhookPayload) -> dict[str, Any]:
        """Process webhook payload and return summary."""
        processed = 0
        duplicates = 0
        errors = 0

        for tx in payload.transactions:
            sig = tx.get("signature", "")

            # Idempotency check
            if self.seen_signatures.contains(sig):
                duplicates += 1
                logger.debug("duplicate_transaction", tx_sig=sig)
                continue

            # Parse transaction
            event = self.parser.parse_transaction(tx)
            if event is None:
                continue

            # Mark as seen
            self.seen_signatures.add(sig, True)

            # Log the event (Stage 1 - logging only)
            logger.info(
                "event_received",
                event_type=event.event_type.value,
                tx_sig=event.tx_signature,
                token=getattr(event, "token_address", None),
            )

            processed += 1

        return {
            "status": "ok",
            "processed": processed,
            "duplicates": duplicates,
            "errors": errors,
        }


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application with dependency injection."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
        title="SolMem Trading Bot",
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
            payload = HeliusWebhookPayload.model_validate(raw_body)
            result = await handler.handle(payload)
            return JSONResponse(content=result, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("webhook_error", error=str(e))
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return app


# Default app instance for uvicorn
app = create_app()
