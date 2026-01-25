# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important Files

- **claude_memory.md** - Task-specific instructions, active decisions, session notes. Check this first.
- **claude_roadmap.md** - Project roadmap with current stage and remaining tasks.

## Project Overview

Solana memecoin trading bot (sniper) for Pump.fun pre-migration trades. Strategy: buy on bonding curve → sell 75% pre-migration + 25% via Jupiter post-launch.

## Tech Stack

- Python 3.12, asyncio
- FastAPI (webhook server)
- Pydantic (validation/settings)
- structlog (JSON logging, Prometheus-ready)
- solana-py
- Docker

## Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run webhook server
uvicorn src.webhook.server:app --reload --port 8000

# Run tests
pytest
pytest tests/unit/  # unit only
pytest -k "test_name"  # single test

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/

# Local webhook testing
ngrok http 8000

# Docker
docker-compose -f docker/docker-compose.yml up --build
```

## Architecture

### Current Stage: Helius Webhook Integration

```
Helius Webhook → POST /webhook → EventParser → Filters → Logger
```

- **Webhook endpoint**: Receives Pump.fun events (token creations, bonding curve progress, migrations)
- **Event parser**: Raw Helius payload → structured Pydantic models (token_address, curve_progress, liquidity_SOL, dev_holds)
- **Filters**: Config-driven thresholds applied before processing
- **Idempotency**: Dedupe by tx_signature

### Planned Modules

```
src/
├── config/        # YAML/JSON config loading, Pydantic Settings
├── webhook/       # FastAPI server, Helius payload parsing
├── filters/       # Token filtering logic (thresholds, blacklists)
├── trading/       # Buy/sell execution (bonding curve, Jupiter)
├── rpc/           # Multi-endpoint RPC client with retries
├── models/        # Pydantic models for events, tokens, trades
├── metrics/       # Prometheus metrics export
└── utils/         # Retry decorators, circuit breakers
```

## Config System

All thresholds and behavior controlled via config (not hardcoded):
- Wallet addresses, RPC endpoints
- Filter thresholds (min liquidity, max dev holds, curve progress)
- Trade limits (max per-trade SOL, max loss)
- Mode: `dry-run` | `devnet` | `mainnet`

## Security

**NEVER commit secrets to git.** All API keys and private keys stored in `.env` file (gitignored). Copy `.env.example` to `.env` and fill in real values. Use `BOT_` prefix for env vars.

## Financial Data Accuracy

**NEVER use estimated/fallback values for prices, PnL, or financial calculations.** This is real money.

- Only use actual price from swap data: `price = SOL_amount / token_amount`
- If real data unavailable → return `None`, never guess
- No "rough estimates" from liquidity or other proxies
- No circular calculations (price → market_cap → price)
- Wrong data is worse than no data

## Key Patterns

- **Reliability**: Exponential backoff retries, timeouts, circuit breakers
- **Observability**: Every event logged with context (timestamp, wallet, event_type, metrics)
- **Safety**: Dry-run mode logs trades without execution; devnet testing before mainnet
- **Validation**: Strict Pydantic validation; invalid events dropped with warning log

## Testing

- pytest with >80% coverage target
- Each module runnable/testable independently
- Test with ngrok + devnet Pump.fun events before mainnet