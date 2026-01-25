"""Dexscreener API client for fetching token pair data."""

from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel

from src.config import Settings
from src.utils import get_logger

logger = get_logger(__name__)


class PairData(BaseModel):
    """Parsed pair data from Dexscreener."""

    pair_address: str
    dex_id: str  # "raydium", "pumpswap", etc.
    base_token: str  # Token mint address
    quote_token: str  # Usually SOL

    # Market data
    price_usd: float | None = None
    market_cap_usd: float | None = None
    volume_1h_usd: float | None = None
    volume_24h_usd: float | None = None
    liquidity_usd: float | None = None

    # Pair info
    pair_created_at: datetime | None = None
    age_minutes: float | None = None

    # Links
    url: str | None = None

    @property
    def chart_url(self) -> str:
        """Dexscreener chart URL."""
        return f"https://dexscreener.com/solana/{self.pair_address}"


class DexscreenerClient:
    """Client for Dexscreener API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.dexscreener.base_url
        self.timeout = settings.dexscreener.timeout_seconds
        self.max_retries = settings.dexscreener.max_retries

    async def get_pairs_by_token(self, token_address: str) -> list[PairData]:
        """Fetch all pairs for a token from Dexscreener.

        Returns pairs sorted by liquidity (highest first).
        """
        url = f"{self.base_url}/latest/dex/tokens/{token_address}"

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()

                    pairs = self._parse_pairs(data, token_address)
                    logger.info(
                        "dexscreener_pairs_fetched",
                        token=token_address,
                        pairs_found=len(pairs),
                    )
                    return pairs

            except httpx.TimeoutException:
                logger.warning(
                    "dexscreener_timeout",
                    token=token_address,
                    attempt=attempt + 1,
                )
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "dexscreener_http_error",
                    token=token_address,
                    status=e.response.status_code,
                    attempt=attempt + 1,
                )
            except Exception as e:
                logger.exception(
                    "dexscreener_error",
                    token=token_address,
                    error=str(e),
                )
                break

        return []

    async def get_raydium_or_pumpswap_pair(self, token_address: str) -> PairData | None:
        """Get the best Raydium or PumpSwap pair for a token.

        Returns the pair with highest liquidity on Raydium or PumpSwap,
        or None if no such pair exists.
        """
        pairs = await self.get_pairs_by_token(token_address)

        # Filter for Raydium or PumpSwap pairs on Solana
        target_dexes = {"raydium", "pumpswap"}
        matching_pairs = [
            p for p in pairs
            if p.dex_id.lower() in target_dexes
        ]

        if not matching_pairs:
            logger.debug(
                "no_raydium_pumpswap_pair",
                token=token_address,
                total_pairs=len(pairs),
            )
            return None

        # Return highest liquidity pair
        best_pair = max(
            matching_pairs,
            key=lambda p: p.liquidity_usd or 0
        )

        logger.info(
            "raydium_pumpswap_pair_found",
            token=token_address,
            dex=best_pair.dex_id,
            mc=best_pair.market_cap_usd,
            vol_1h=best_pair.volume_1h_usd,
            age_min=best_pair.age_minutes,
        )

        return best_pair

    def _parse_pairs(self, data: dict[str, Any], token_address: str) -> list[PairData]:
        """Parse Dexscreener API response into PairData objects."""
        pairs: list[PairData] = []

        raw_pairs = data.get("pairs") or []
        now = datetime.now(UTC)

        for raw in raw_pairs:
            try:
                # Only Solana pairs
                if raw.get("chainId") != "solana":
                    continue

                # Parse creation time and calculate age
                pair_created_at = None
                age_minutes = None
                if created_ts := raw.get("pairCreatedAt"):
                    pair_created_at = datetime.fromtimestamp(created_ts / 1000, tz=UTC)
                    age_minutes = (now - pair_created_at).total_seconds() / 60

                # Extract volume data
                volume_data = raw.get("volume") or {}

                pair = PairData(
                    pair_address=raw.get("pairAddress", ""),
                    dex_id=raw.get("dexId", ""),
                    base_token=raw.get("baseToken", {}).get("address", ""),
                    quote_token=raw.get("quoteToken", {}).get("address", ""),
                    price_usd=self._safe_float(raw.get("priceUsd")),
                    market_cap_usd=self._safe_float(raw.get("marketCap")),
                    volume_1h_usd=self._safe_float(volume_data.get("h1")),
                    volume_24h_usd=self._safe_float(volume_data.get("h24")),
                    liquidity_usd=self._safe_float(raw.get("liquidity", {}).get("usd")),
                    pair_created_at=pair_created_at,
                    age_minutes=age_minutes,
                    url=raw.get("url"),
                )
                pairs.append(pair)

            except Exception as e:
                logger.warning(
                    "dexscreener_parse_error",
                    error=str(e),
                    pair_address=raw.get("pairAddress"),
                )

        # Sort by liquidity (highest first)
        pairs.sort(key=lambda p: p.liquidity_usd or 0, reverse=True)
        return pairs

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        """Safely convert value to float, returning None on failure."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None