from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.config import Settings, get_settings
from src.models.events import (
    CurveProgressEvent,
    EventType,
    HeliusWebhookPayload,
    MigrationEvent,
    TokenCreatedEvent,
)
from src.signals import OutcomeTracker, SignalGenerator, SignalStorage
from src.utils import get_logger, setup_logging
from src.webhook.idempotency import IdempotencyStore
from src.webhook.parser import EventParser

logger = get_logger(__name__)


class WebhookHandler:
    """Handles incoming Helius webhooks."""

    signal_storage: SignalStorage | None
    signal_generator: SignalGenerator | None
    outcome_tracker: OutcomeTracker | None

    def __init__(
        self,
        settings: Settings,
        signal_storage: SignalStorage | None = None,
    ):
        self.settings = settings
        self.parser = EventParser()
        self.seen_signatures: IdempotencyStore[bool] = IdempotencyStore(max_size=10000)

        # Signals module for paper trading (controlled by config)
        self.signals_enabled = settings.signals.enabled
        if self.signals_enabled:
            self.signal_storage = signal_storage or SignalStorage(
                db_path=Path(settings.signals.db_path)
            )
            self.signal_generator = SignalGenerator(
                self.signal_storage,
                settings,
                simulated_buy_sol=Decimal(str(settings.signals.simulated_buy_sol)),
            )
            self.outcome_tracker = OutcomeTracker(
                self.signal_storage,
                expiry_hours=settings.signals.expiry_hours,
            )
            logger.info(
                "signals_module_enabled",
                db_path=settings.signals.db_path,
                simulated_buy_sol=settings.signals.simulated_buy_sol,
            )
        else:
            self.signal_storage = None
            self.signal_generator = None
            self.outcome_tracker = None
            logger.info("signals_module_disabled")

    async def handle(self, payload: HeliusWebhookPayload) -> dict[str, Any]:
        """Process webhook payload and return summary."""
        processed = 0
        duplicates = 0
        errors = 0
        signals_generated = 0

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

            # Log the event
            logger.info(
                "event_received",
                event_type=event.event_type.value,
                tx_sig=event.tx_signature,
                token=getattr(event, "token_address", None),
            )

            # Process for signals (paper trading)
            if self.signals_enabled:
                signal = self._process_for_signals(event)
                if signal:
                    signals_generated += 1

            processed += 1

        return {
            "status": "ok",
            "processed": processed,
            "duplicates": duplicates,
            "errors": errors,
            "signals_generated": signals_generated,
        }

    def _process_for_signals(self, event: Any) -> Any:
        """Process event for signal generation/tracking."""
        if not self.signals_enabled:
            return None

        # Type narrowing for mypy - these are guaranteed non-None when signals_enabled
        assert self.signal_generator is not None
        assert self.outcome_tracker is not None

        # Handle based on event type
        if event.event_type == EventType.CURVE_PROGRESS:
            assert isinstance(event, CurveProgressEvent)
            # First check if this updates an existing signal
            self.outcome_tracker.handle_curve_update(event)
            # Then check if this creates a new signal
            return self.signal_generator.evaluate_curve_progress(event)

        elif event.event_type == EventType.TOKEN_CREATED:
            assert isinstance(event, TokenCreatedEvent)
            return self.signal_generator.evaluate_token_created(event)

        elif event.event_type == EventType.MIGRATION:
            assert isinstance(event, MigrationEvent)
            return self.outcome_tracker.handle_migration(event)

        return None


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

    @app.get("/signals/stats")
    async def signals_stats() -> JSONResponse:
        """Get signal statistics for paper trading analysis."""
        if not handler.signals_enabled or not handler.signal_storage:
            return JSONResponse(
                content={"error": "signals not enabled"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        stats = handler.signal_storage.get_stats()
        return JSONResponse(content=stats, status_code=status.HTTP_200_OK)

    @app.get("/signals/recent")
    async def signals_recent(hours: int = 24, limit: int = 50) -> JSONResponse:
        """Get recent signals for paper trading analysis."""
        if not handler.signals_enabled or not handler.signal_storage:
            return JSONResponse(
                content={"error": "signals not enabled"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        signals = handler.signal_storage.get_recent(hours=hours, limit=limit)
        return JSONResponse(
            content=[s.model_dump(mode="json") for s in signals],
            status_code=status.HTTP_200_OK,
        )

    return app


# Default app instance for uvicorn
app = create_app()
