# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Files

- **claude_memory.md** - Task-specific instructions, active decisions, session notes. Check this first.
- **claude_roadmap.md** - Project roadmap with current stage and remaining tasks.

## Project Overview

**Pump.fun Migration Signal Bot** - Detects Pump.fun token migrations to Raydium/PumpSwap, enriches with Dexscreener data, filters by configurable thresholds, and logs signals (Telegram coming soon).

**Data Flow:**
```
Helius Webhook (Pump.fun) → Detect Migration → Extract token_mint → Dexscreener API → Filter (MC/Vol/Age) → Log Signal
```

## Tech Stack

- Python 3.12, asyncio
- FastAPI (webhook server)
- Pydantic (validation/settings)
- structlog (JSON logging)
- httpx (async HTTP client)

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run webhook server
uvicorn src.webhook.server:app --reload --port 8000

# Run tests
pytest
pytest -k "test_name"  # single test

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/

# Local webhook testing
ngrok http 8000

# Helius webhook management
python scripts/setup_helius_webhook.py                      # List webhooks
python scripts/setup_helius_webhook.py <url>                # Create webhook
python scripts/setup_helius_webhook.py --delete <id>        # Delete webhook
```

## Architecture

### Current Flow

```
Helius Webhook (Pump.fun program)
         ↓
    Migration Detection (src/webhook/server.py)
    - source == "PUMP_FUN"
    - Extract token_mint
    - Check for Raydium/PumpSwap involvement
         ↓
    Dexscreener Enrichment (src/enrichment/dexscreener.py)
    - Fetch pair data for token
    - Get MC, 1h volume, age
         ↓
    Filter (configurable thresholds)
    - MC > min_market_cap_usd
    - Vol(1h) > min_volume_1h_usd
    - Age < max_age_minutes
         ↓
    Log Signal (Telegram coming soon)
```

### Project Structure

```
.
├── .claude/           # Claude Code instructions and memory
├── config/            # YAML config (config.example.yaml)
├── docker/            # Dockerfile and docker-compose
├── scripts/           # setup_helius_webhook.py
├── src/
│   ├── config/        # Pydantic Settings, YAML loading
│   ├── enrichment/    # Dexscreener API client
│   ├── filters/       # Filter base classes (for future use)
│   ├── models/        # MigrationEvent, SignalEvent
│   ├── utils/         # Logging setup
│   └── webhook/       # FastAPI server, MigrationParser
└── tests/             # pytest tests
```

## Filter Thresholds

All configurable in config.yaml:
- **min_market_cap_usd**: 10000 (MC > $10,000)
- **min_volume_1h_usd**: 5000 (1h Vol > $5,000)
- **max_age_minutes**: 30 (Age < 30 min)

## External APIs

| API | Purpose | Endpoint |
|-----|---------|----------|
| Helius | Pump.fun events | Webhook |
| Dexscreener | MC, Volume, Age | `api.dexscreener.com` |

## Security

**NEVER commit secrets to git.** Required in `.env`:
- `BOT_HELIUS_API_KEY` - Helius API key
- `BOT_TELEGRAM_TOKEN` - Telegram bot token (future)
- `BOT_TELEGRAM_CHAT_ID` - Target chat ID (future)

## Data Accuracy

**NEVER use estimated/fallback values for prices, MC, or financial data.**

- Only use data from Dexscreener API
- If data unavailable → skip signal, never guess
- Wrong data is worse than no data

## Key Patterns

- **Reliability**: Retries with backoff for Dexscreener
- **Observability**: Every event logged with context
- **Validation**: Strict Pydantic validation
- **Idempotency**: tx_signature deduplication

## Testing

- pytest with coverage
- Mock Dexscreener in unit tests
- Test with ngrok + real Helius webhooks