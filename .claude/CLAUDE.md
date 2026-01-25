# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Files

- **claude_memory.md** - Active decisions, session notes. Check this first.
- **claude_roadmap.md** - Project roadmap with current stage.

## Project Overview

**Solana Memecoin Signal Bot** - Detects new token opportunities on Solana, enriches with Dexscreener data, filters by configurable thresholds, sends signals.

**Current Source**: Pump.fun migrations (first implementation)
**Future Sources**: BONK, BAGS, other Solana memecoins

**Data Flow:**
```
Helius Webhook → Detect Event → Extract token_mint → Dexscreener API → Filter (MC/Vol/Age) → Signal
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

### Current Flow (Pump.fun Migrations)

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
    Signal Output
```

### Project Structure

```
src/
├── config/        # Pydantic Settings, YAML loading
├── enrichment/    # Dexscreener API client
├── filters/       # Filter base classes
├── models/        # MigrationEvent, SignalEvent
├── utils/         # Logging setup
└── webhook/       # FastAPI server, MigrationParser
```

## Filter Thresholds

All configurable in config.yaml:
```yaml
filters:
  min_market_cap_usd: 10000   # MC > $10k
  min_volume_1h_usd: 5000     # 1h Vol > $5k
  max_age_minutes: 30         # Age < 30 min
```

## External APIs

| API | Purpose |
|-----|---------|
| Helius | Blockchain events (webhooks) |
| Dexscreener | MC, Volume, Age, Price |

## Security

**NEVER commit secrets to git.** Required in `.env`:
- `BOT_HELIUS_API_KEY` - Helius API key
- `BOT_TELEGRAM_TOKEN` - Telegram bot token
- `BOT_TELEGRAM_CHAT_ID` - Target chat ID

## Data Accuracy

**NEVER use estimated/fallback values for MC, volume, or financial data.**

- Only use data from Dexscreener API
- If data unavailable → skip signal
- Wrong data is worse than no data