# Roadmap

## Solana Memecoin Signal Bot

---

## Stage 1: Infrastructure ✅

- [x] FastAPI webhook server
- [x] Config system (Pydantic + YAML)
- [x] Idempotency (tx_signature)
- [x] Structured logging
- [x] Tests

---

## Stage 2: Pump.fun ← CURRENT

- [x] Helius webhook for Pump.fun
- [x] MigrationParser
- [x] DexscreenerClient
- [x] Configurable filters (MC/Vol/Age)
- [x] Signal output to console
- [ ] Test with live data
- [ ] Telegram notifications

---

## Future

- Additional sources (BONK, BAGS, etc.)
- Holder analysis
- ML scoring