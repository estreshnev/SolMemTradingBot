"""Configuration settings for Raydium Signal Bot."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunMode(str, Enum):
    DRY_RUN = "dry-run"
    DEVNET = "devnet"
    MAINNET = "mainnet"


class WebhookConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    secret: str | None = None


class RPCConfig(BaseModel):
    url: str = "https://api.mainnet-beta.solana.com"
    timeout_ms: int = 5000
    max_retries: int = 3


class FilterThresholds(BaseModel):
    """Filter thresholds for Raydium pool signals."""

    min_market_cap_usd: float = 10000  # MC > $10,000
    min_volume_24h_usd: float = 5000  # Volume > $5,000
    max_top10_holders_pct: float = 30  # Top 10 holders < 30%
    min_liquidity_usd: float = 5000  # Liquidity > $5,000
    max_pool_age_hours: float = 24  # Only new pools


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    enabled: bool = False
    bot_token: str | None = None
    chat_id: str | None = None
    rate_limit_per_minute: int = 20


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    mode: RunMode = RunMode.DRY_RUN
    log_level: str = "INFO"

    # Secrets - loaded from env vars only, never from YAML
    helius_api_key: SecretStr | None = None
    telegram_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    rpc_url: str | None = None

    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    rpc: RPCConfig = Field(default_factory=RPCConfig)
    filters: FilterThresholds = Field(default_factory=FilterThresholds)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        """Load settings from YAML file, with env vars taking precedence."""
        yaml_config: dict[str, Any] = {}
        if path.exists():
            with open(path) as f:
                yaml_config = yaml.safe_load(f) or {}
        return cls(**yaml_config)


@lru_cache
def get_settings(config_path: str | None = None) -> Settings:
    """Get cached settings instance."""
    if config_path:
        return Settings.from_yaml(Path(config_path))

    # Try default locations
    for default_path in [Path("config/config.yaml"), Path("config.yaml")]:
        if default_path.exists():
            return Settings.from_yaml(default_path)

    return Settings()