# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Files

- **claude_memory.md** - Task-specific instructions, active decisions, session notes. Check this first.
- **claude_roadmap.md** - Project roadmap with current stage and remaining tasks.

## Project Overview

**Solana memecoin signal bot** - Detects new Raydium pool creations, enriches with market data, filters by quality metrics, and sends Telegram notifications. ML scoring planned for future.

**Data Flow:**
```
Helius Webhook (Raydium pool) → Dexscreener (MC/Vol) → RPC (holders) → Filters → Telegram
```

## Tech Stack

- Python 3.12, asyncio
- FastAPI (webhook server)
- Pydantic (validation/settings)
- structlog (JSON logging)
- httpx (async HTTP client)
- python-telegram-bot (planned)

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

### Target Architecture

```
Helius Webhook (Raydium pool creation)
         ↓
    Pool Detection (src/webhook/)
         ↓
    Data Enrichment (src/enrichment/) [TODO]
    ├── Dexscreener API → MC, Volume, Age, Price
    └── RPC → Top 10 holders %
         ↓
    Filters (src/filters/)
    ├── MC > $10,000
    ├── Volume > $5,000
    └── Top 10 holders < 30%
         ↓
    Score Calculation
         ↓
    Telegram Signal (src/telegram/) [TODO]
```

### Project Structure

```
.
├── .claude/           # Claude Code instructions and memory
├── config/            # YAML config (config.example.yaml)
├── docker/            # Dockerfile and docker-compose
├── scripts/           # Utility scripts (setup_helius_webhook.py)
├── src/
│   ├── config/        # Pydantic Settings, YAML loading
│   ├── filters/       # Signal filtering logic (base classes)
│   ├── models/        # Pydantic models (RaydiumPoolCreated)
│   ├── utils/         # Logging setup
│   └── webhook/       # FastAPI server, idempotency
└── tests/             # pytest tests
```

## Filter Thresholds

Default thresholds (configurable in config.yaml):
- **Market Cap**: > $10,000
- **24h Volume**: > $5,000
- **Top 10 Holders**: < 30%
- **Liquidity**: > $5,000
- **Pool Age**: < 24 hours

## External APIs

| API | Purpose | Endpoint |
|-----|---------|----------|
| Helius | Pool creation events | Webhook |
| Dexscreener | MC, Volume, Price | `api.dexscreener.com` |
| Solana RPC | Holder analysis | Configurable |
| Telegram | Send signals | Bot API |

## Security

**NEVER commit secrets to git.** Required in `.env`:
- `BOT_HELIUS_API_KEY` - Helius API key
- `BOT_TELEGRAM_TOKEN` - Telegram bot token
- `BOT_TELEGRAM_CHAT_ID` - Target chat/channel ID
- `BOT_RPC_URL` - Solana RPC endpoint

## Data Accuracy

**NEVER use estimated/fallback values for prices, MC, or financial data.**

- Only use data from authoritative sources (Dexscreener, RPC)
- If real data unavailable → return `None`, never guess
- Wrong data is worse than no data

## Key Patterns

- **Reliability**: Exponential backoff retries, timeouts
- **Observability**: Every event logged with context
- **Validation**: Strict Pydantic validation
- **Rate Limiting**: Respect API rate limits

## Testing

- pytest with coverage
- Each module runnable/testable independently
- Mock external APIs in tests