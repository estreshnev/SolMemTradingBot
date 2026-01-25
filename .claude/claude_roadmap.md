# Project Roadmap

## Current: Pump.fun Migration Signal Bot

---

## Stage 1: Core Infrastructure ✅ COMPLETE

- [x] Project scaffolding
- [x] Config system (Pydantic Settings, YAML)
- [x] Webhook server (FastAPI)
- [x] Idempotency layer
- [x] Structured logging
- [x] Test suite

---

## Stage 2: Migration Detection + Dexscreener ✅ COMPLETE

- [x] Helius webhook for Pump.fun program
- [x] MigrationParser - detect migrations
- [x] Extract token_mint from transactions
- [x] DexscreenerClient - fetch pair data
- [x] Filter by MC, 1h volume, age
- [x] Configurable thresholds in config.yaml
- [x] Log signals to console

---

## Stage 3: Telegram Notifications ← NEXT

- [ ] Telegram bot integration
- [ ] Send signals to chat/channel
- [ ] Rate limiting
- [ ] Error handling

---

## Stage 4: Refinement

- [ ] Test with live migrations
- [ ] Tune filter thresholds
- [ ] Add more signal details
- [ ] Improve migration detection accuracy

---

## Future

- Holder analysis (RPC)
- ML scoring
- Multi-DEX support
- Dashboard/UI