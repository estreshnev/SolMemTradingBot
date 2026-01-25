# Claude Memory

## Project

Solana Memecoin Signal Bot - Python 3.12, personal use

## Current: Pump.fun Migrations

```
Helius (Pump.fun) → MigrationParser → DexscreenerClient → Filter → Signal
```

**Detection**: source == "PUMP_FUN" + Raydium/PumpSwap involvement

## Filters (config.yaml)

```yaml
min_market_cap_usd: 10000   # MC > $10k
min_volume_1h_usd: 5000     # 1h Vol > $5k
max_age_minutes: 30         # Age < 30 min
```

## Program IDs

- Pump.fun: `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`
- Raydium AMM: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- Raydium CLMM: `CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK`
- PumpSwap: `pSwpGyAJiLMTUidSTPXhNFyJz3aLH41mGqhW3s1hkLd`

## Rules

- No fallback data - skip signal if Dexscreener unavailable
- Config-driven thresholds
- Secrets in .env only