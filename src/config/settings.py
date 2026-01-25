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
    endpoints: list[str] = Field(default_factory=lambda: ["https://api.devnet.solana.com"])
    timeout_ms: int = 5000
    max_retries: int = 3


class FilterThresholds(BaseModel):
    min_liquidity_sol: float = 0.0
    max_dev_holds_pct: float = 100.0
    min_curve_progress_pct: float = 0.0
    max_curve_progress_pct: float = 100.0


class TradeLimits(BaseModel):
    max_sol_per_trade: float = 0.1
    max_daily_loss_sol: float = 1.0
    max_open_positions: int = 5


class SignalsConfig(BaseModel):
    """Configuration for paper trading signals."""

    enabled: bool = True
    db_path: str = "data/signals.db"
    simulated_buy_sol: float = 0.1  # SOL amount for simulated trades
    expiry_hours: int = 24  # Mark signals expired after this time


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    mode: RunMode = RunMode.DRY_RUN
    log_level: str = "INFO"

    # Secrets - loaded from env vars only, never from YAML
    wallet_private_key: SecretStr | None = None
    helius_api_key: SecretStr | None = None

    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    rpc: RPCConfig = Field(default_factory=RPCConfig)
    filters: FilterThresholds = Field(default_factory=FilterThresholds)
    limits: TradeLimits = Field(default_factory=TradeLimits)
    signals: SignalsConfig = Field(default_factory=SignalsConfig)

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
