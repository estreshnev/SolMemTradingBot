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


class FilterThresholds(BaseModel):
    """Filter thresholds for migration signals."""

    min_market_cap_usd: float = 10000  # MC > $10,000
    min_volume_1h_usd: float = 5000  # 1h Volume > $5,000
    max_age_minutes: float = 30  # Age < 30 minutes


class DexscreenerConfig(BaseModel):
    """Dexscreener API configuration."""

    base_url: str = "https://api.dexscreener.com"
    timeout_seconds: float = 10.0
    max_retries: int = 3


class TelegramConfig(BaseModel):
    """Telegram bot configuration."""

    enabled: bool = False
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

    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    filters: FilterThresholds = Field(default_factory=FilterThresholds)
    dexscreener: DexscreenerConfig = Field(default_factory=DexscreenerConfig)
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