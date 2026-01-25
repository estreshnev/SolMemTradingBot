# Claude Memory

Persistent context for Claude Code sessions. Update this file when important decisions are made or patterns established.

## Project Context

- **Type**: Solana memecoin signal bot (Raydium pool detection)
- **Language**: Python 3.12 with strict typing
- **User**: Personal use, single instance
- **Goal**: Detect new Raydium pools → enrich with data → filter → send Telegram signals

## Project Pivot (2026-01-25)

**Changed from**: Pump.fun sniper bot (auto-trading)
**Changed to**: Raydium signal bot with ML scoring (notifications only)

**Reason**: Focus on signal quality and ML analysis before any trading

## Active Decisions

- Config-driven: All thresholds/behavior in YAML/JSON, never hardcoded
- **Signal-only mode**: No auto-trading, just Telegram notifications
- Idempotency via `tx_signature` to handle duplicate webhooks
- **Secrets in .env only**: All API keys, private keys, RPC URLs → `.env` file (gitignored)

## Critical: No Fallback Calculations

**NEVER use estimated/fallback values for prices, MC, or any financial data.**

- If actual data is unavailable, return `None` - do not guess
- Only use data from authoritative sources (Dexscreener, RPC)
- Wrong data is worse than no data

## Data Flow

```
Helius Webhook (Raydium pool creation)
         ↓
    Pool Detection
         ↓
    Data Enrichment
    ├── Dexscreener → MC, Volume, Age, Price
    └── RPC → Top 10 holders %
         ↓
    Filters
    ├── MC > $10,000
    ├── Volume > $5,000
    └── Top 10 holders < 30%
         ↓
    Score Calculation
         ↓
    Telegram Signal
```

## External APIs

| API | Purpose | Rate Limits |
|-----|---------|-------------|
| Helius | Webhook events | Based on plan |
| Dexscreener | MC, Volume, Price | ~300/min |
| Solana RPC | Holder analysis | Based on provider |
| Telegram | Send signals | 30 msg/sec |

## Filter Thresholds (Configurable)

```yaml
filters:
  min_market_cap_usd: 10000
  min_volume_24h_usd: 5000
  max_top10_holders_pct: 30
  min_liquidity_usd: 5000
  max_pool_age_hours: 24  # Only new pools
```

## Code Style

- async/await everywhere (no blocking calls)
- Pydantic models for all data structures
- structlog with JSON output for all logging
- Type hints required on all functions

## Architecture Notes

**Single-instance design**: Personal use only. SQLite for storage. No need for horizontal scaling.

## Key Files to Modify

For the new direction, these files need updates:
- `src/webhook/parser.py` - Detect Raydium instead of Pump.fun
- `src/config/settings.py` - New filter thresholds
- `src/signals/` - Repurpose for pool signals
- New: `src/enrichment/` - Dexscreener + RPC data fetching
- New: `src/telegram/` - Telegram bot integration