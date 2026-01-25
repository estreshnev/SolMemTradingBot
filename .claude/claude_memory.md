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

- Config-driven: All thresholds/behavior in YAML, never hardcoded
- **Signal-only mode**: No auto-trading, just Telegram notifications
- Idempotency via `tx_signature` to handle duplicate webhooks
- **Secrets in .env only**: All API keys, RPC URLs → `.env` file (gitignored)

## Critical: No Fallback Calculations

**NEVER use estimated/fallback values for prices, MC, or any financial data.**

- If actual data is unavailable, return `None` - do not guess
- Only use data from authoritative sources (Dexscreener, RPC)
- Wrong data is worse than no data

## Data Flow

```
Helius Webhook (Raydium pool creation)
         ↓
    Pool Detection (src/webhook/)
         ↓
    Data Enrichment [TODO: src/enrichment/]
    ├── Dexscreener → MC, Volume, Age, Price
    └── RPC → Top 10 holders %
         ↓
    Filters (src/filters/)
    ├── MC > $10,000
    ├── Volume > $5,000
    └── Top 10 holders < 30%
         ↓
    Score Calculation
         ↓
    Telegram Signal [TODO: src/telegram/]
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

## Raydium Program IDs

- **AMM**: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- **CLMM**: `CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK`

## Current Project Structure

```
src/
├── config/        # Settings (FilterThresholds, TelegramConfig)
├── filters/       # BaseFilter, FilterChain, FilterResult
├── models/        # HeliusWebhookPayload, RaydiumPoolCreated
├── utils/         # Logging setup (structlog)
└── webhook/       # FastAPI server, IdempotencyStore
```

## Next Steps (Stage 2)

1. Implement Raydium pool detection parser
2. Create `src/enrichment/` for Dexscreener + RPC
3. Create `src/telegram/` for notifications
4. Implement filters with new thresholds