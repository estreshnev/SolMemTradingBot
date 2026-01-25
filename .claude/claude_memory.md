# Claude Memory

Persistent context for Claude Code sessions.

## Project Context

- **Type**: Solana memecoin signal bot
- **Language**: Python 3.12 with strict typing
- **User**: Personal use, single instance
- **Current**: Pump.fun migrations (first source)
- **Future**: BONK, BAGS, other Solana tokens

## Current Implementation (Pump.fun)

```
Helius Webhook (Pump.fun)
         ↓
    MigrationParser.parse()
    - source == "PUMP_FUN"
    - Extract token_mint
    - Check for Raydium/PumpSwap
         ↓
    DexscreenerClient.get_raydium_or_pumpswap_pair()
    - Fetch MC, 1h vol, age
         ↓
    Filter (settings.filters)
         ↓
    Log SignalEvent
```

## Active Decisions

- **Config-driven**: All thresholds in config.yaml
- **Signal-only mode**: No auto-trading
- **Idempotency**: tx_signature deduplication
- **Secrets in .env**: API keys only

## Critical: No Fallback Data

**NEVER use estimated/fallback values for MC, volume, or financial data.**

- If Dexscreener data unavailable → skip signal
- Wrong data is worse than no data

## Filter Thresholds

```yaml
filters:
  min_market_cap_usd: 10000   # MC > $10k
  min_volume_1h_usd: 5000     # 1h Vol > $5k
  max_age_minutes: 30         # Age < 30 min
```

## Program IDs

- **Pump.fun**: `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
- **Raydium AMM**: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- **Raydium CLMM**: `CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK`
- **PumpSwap**: `pSwpGyAJiLMTUidSTPXhNFyJz3aLH41mGqhW3s1hkLd`

## Code Style

- async/await everywhere
- Pydantic models for all data
- structlog JSON logging
- Type hints required