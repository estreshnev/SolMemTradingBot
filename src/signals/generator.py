"""Signal generator - evaluates events and creates buy signals."""

import uuid
from decimal import Decimal

import structlog

from src.config.settings import FilterThresholds, Settings
from src.models.events import CurveProgressEvent, TokenCreatedEvent
from src.signals.models import Signal
from src.signals.storage import SignalStorage

logger = structlog.get_logger()


class SignalGenerator:
    """Evaluates incoming events against thresholds and generates signals."""

    def __init__(
        self,
        storage: SignalStorage,
        settings: Settings,
        simulated_buy_sol: Decimal | None = None,
    ):
        self.storage = storage
        self.settings = settings
        self.filters = settings.filters
        self.simulated_buy_sol = simulated_buy_sol or Decimal(
            str(settings.limits.max_sol_per_trade)
        )

        # Track tokens we've already signaled to avoid duplicates
        self._signaled_tokens: set[str] = set()

    def evaluate_curve_progress(self, event: CurveProgressEvent) -> Signal | None:
        """Evaluate a curve progress event for signal generation.

        Returns a Signal if all filter conditions pass, None otherwise.
        """
        token = event.token_address
        log = logger.bind(token=token, event_type="curve_progress")

        # Skip if already signaled
        if token in self._signaled_tokens:
            log.debug("signal_skipped_duplicate")
            return None

        # Check filters
        rejection = self._check_filters(event)
        if rejection:
            log.debug("signal_rejected", reason=rejection)
            return None

        # All filters passed - create signal
        signal = Signal(
            id=str(uuid.uuid4()),
            token_address=token,
            trigger_tx_signature=event.tx_signature,
            signal_time=event.timestamp,
            entry_curve_progress_pct=event.curve_progress_pct,
            entry_liquidity_sol=Decimal(str(event.liquidity_sol)),
            entry_market_cap_sol=(
                Decimal(str(event.market_cap_sol)) if event.market_cap_sol else None
            ),
            entry_price_sol=self._estimate_price(event),
            simulated_buy_sol=self.simulated_buy_sol,
            raw_event=event.model_dump(mode="json"),
        )

        # Save and track
        self.storage.save(signal)
        self._signaled_tokens.add(token)

        log.info(
            "signal_generated",
            signal_id=signal.id,
            curve_pct=event.curve_progress_pct,
            liquidity=event.liquidity_sol,
            price=float(signal.entry_price_sol) if signal.entry_price_sol else None,
            market_cap=float(signal.entry_market_cap_sol) if signal.entry_market_cap_sol else None,
        )

        return signal

    def evaluate_token_created(self, event: TokenCreatedEvent) -> Signal | None:
        """Evaluate a token creation event for signal generation.

        Typically we want curve progress events, but can signal on creation
        if configured to do so.
        """
        token = event.token_address
        log = logger.bind(token=token, event_type="token_created")

        if token in self._signaled_tokens:
            log.debug("signal_skipped_duplicate")
            return None

        # For token creation, we have limited data - just log for now
        # Real implementation would check initial liquidity thresholds
        if event.initial_liquidity_sol < self.filters.min_liquidity_sol:
            log.debug(
                "signal_rejected",
                reason="insufficient_initial_liquidity",
                liquidity=event.initial_liquidity_sol,
                min_required=self.filters.min_liquidity_sol,
            )
            return None

        signal = Signal(
            id=str(uuid.uuid4()),
            token_address=token,
            token_name=event.token_name,
            token_symbol=event.token_symbol,
            creator_address=event.creator_address,
            trigger_tx_signature=event.tx_signature,
            signal_time=event.timestamp,
            entry_curve_progress_pct=0.0,  # Just created
            entry_liquidity_sol=Decimal(str(event.initial_liquidity_sol)),
            simulated_buy_sol=self.simulated_buy_sol,
            raw_event=event.model_dump(mode="json"),
        )

        self.storage.save(signal)
        self._signaled_tokens.add(token)

        log.info(
            "signal_generated",
            signal_id=signal.id,
            token_name=event.token_name,
            initial_liquidity=event.initial_liquidity_sol,
        )

        return signal

    def _check_filters(self, event: CurveProgressEvent) -> str | None:
        """Check all filter conditions. Returns rejection reason or None if passed."""
        f = self.filters

        # Liquidity check
        if event.liquidity_sol < f.min_liquidity_sol:
            return f"liquidity_too_low:{event.liquidity_sol}<{f.min_liquidity_sol}"

        # Curve progress range check
        if event.curve_progress_pct < f.min_curve_progress_pct:
            return f"curve_progress_too_low:{event.curve_progress_pct}<{f.min_curve_progress_pct}"

        if event.curve_progress_pct > f.max_curve_progress_pct:
            return f"curve_progress_too_high:{event.curve_progress_pct}>{f.max_curve_progress_pct}"

        # Dev holds check would go here (requires on-chain lookup)
        # if dev_holds_pct > f.max_dev_holds_pct:
        #     return f"dev_holds_too_high:{dev_holds_pct}>{f.max_dev_holds_pct}"

        return None

    def _estimate_price(self, event: CurveProgressEvent) -> Decimal | None:
        """Get token price from swap data or estimate from market cap."""
        # Prefer direct price from swap calculation
        if event.token_price_sol and event.token_price_sol > 0:
            return Decimal(str(event.token_price_sol))

        # Fallback: estimate from market cap
        if event.market_cap_sol and event.market_cap_sol > 0:
            total_supply = Decimal("1_000_000_000")
            return Decimal(str(event.market_cap_sol)) / total_supply

        return None

    def get_signaled_tokens(self) -> set[str]:
        """Get set of tokens we've already signaled."""
        return self._signaled_tokens.copy()

    def clear_signaled_tokens(self) -> None:
        """Clear the signaled tokens set (for testing or reset)."""
        self._signaled_tokens.clear()