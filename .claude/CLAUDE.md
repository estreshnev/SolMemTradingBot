# CLAUDE.md

## Project: Solana Memecoin Signal Bot

Detects token opportunities on Solana, enriches with Dexscreener, filters by thresholds, outputs signals.

**First source**: Pump.fun migrations to Raydium/PumpSwap

## Data Flow

```
Helius Webhook (Pump.fun) → Extract token_mint → Dexscreener API → Filter → Signal
```

## Tech Stack

Python 3.12 | FastAPI | Pydantic | structlog | httpx

## Commands

```bash
pip install -e ".[dev]"                    # Install
uvicorn src.webhook.server:app --reload    # Run server
pytest                                      # Test
ruff check src/ tests/                     # Lint
ngrok http 8000                            # Local webhook

# Helius webhook
python scripts/setup_helius_webhook.py              # List
python scripts/setup_helius_webhook.py <url>        # Create
python scripts/setup_helius_webhook.py --delete <id> # Delete
```

## Filter Thresholds (config.yaml)

```yaml
filters:
  min_market_cap_usd: 10000   # MC > $10k
  min_volume_1h_usd: 5000     # 1h Vol > $5k
  max_age_minutes: 30         # Age < 30 min
```

## Project Structure

```
src/
├── config/        # Settings, YAML loading
├── enrichment/    # DexscreenerClient
├── models/        # MigrationEvent, SignalEvent
├── utils/         # Logging
└── webhook/       # FastAPI server, MigrationParser
```

## Security

Secrets in `.env` only:
- `BOT_HELIUS_API_KEY`
- `BOT_TELEGRAM_TOKEN` (future)
- `BOT_TELEGRAM_CHAT_ID` (future)

## Rules

- **No fallback data** - If Dexscreener unavailable → skip signal
- **Config-driven** - All thresholds in config.yaml
- **Idempotency** - tx_signature deduplication