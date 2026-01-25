# Project Roadmap

## Solana Memecoin Signal Bot

---

## Stage 1: Core Infrastructure ✅

- [x] Project scaffolding
- [x] Config system (Pydantic Settings, YAML)
- [x] Webhook server (FastAPI)
- [x] Idempotency layer
- [x] Structured logging
- [x] Test suite

---

## Stage 2: Pump.fun Migrations ← CURRENT

**Goal**: Detect Pump.fun migrations, enrich with Dexscreener, filter, signal

- [x] Helius webhook for Pump.fun program
- [x] MigrationParser - detect migrations
- [x] Extract token_mint from transactions
- [x] DexscreenerClient - fetch pair data
- [x] Filter by MC, 1h volume, age
- [x] Configurable thresholds in config.yaml
- [x] Log signals to console
- [ ] Test with live migrations
- [ ] Telegram notifications

---

## Stage 3: Additional Sources

- [ ] BONK integration
- [ ] BAGS integration
- [ ] Other Solana memecoins

---

## Stage 4: Enhancements

- [ ] Holder analysis (RPC)
- [ ] ML scoring
- [ ] Dashboard/UI