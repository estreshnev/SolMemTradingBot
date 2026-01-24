# Project Roadmap

## Stage 1: Helius Webhook Integration ← CURRENT

**Goal**: Receive and process Pump.fun events reliably

- [x] Project scaffolding (pyproject.toml, src/ structure, Docker)
- [x] Config system (Pydantic Settings, YAML loading)
- [x] Webhook server (FastAPI POST /webhook endpoint)
- [x] Helius payload parser → structured events (placeholder, needs real payload analysis)
- [x] Event models (TokenCreated, CurveProgress, Migration)
- [ ] Basic filters (liquidity, dev holds, curve progress thresholds)
- [x] Idempotency layer (tx_signature deduplication)
- [x] Structured logging (structlog JSON)
- [x] Test suite (pytest, basic webhook tests)
- [ ] Local testing (ngrok + devnet events)

**Deliverable**: Bot logs all Pump.fun events with filtering applied

---

## Stage 2: Token Analysis

- [ ] On-chain data fetching (token metadata, holder distribution)
- [ ] Dev wallet analysis (past rugs, behavior patterns)
- [ ] Social signals (Twitter/Telegram mentions) - optional
- [ ] Scoring system (configurable weights)

---

## Stage 3: Trade Execution

- [ ] Bonding curve buy logic (Pump.fun SDK/raw instructions)
- [ ] Pre-migration sell (75% exit on curve)
- [ ] Jupiter integration (post-migration 25% exit)
- [ ] Transaction building with priority fees
- [ ] Multi-RPC submission with retries

---

## Stage 4: Position Management

- [ ] Active position tracking
- [ ] Stop-loss / take-profit automation
- [ ] Migration event detection → trigger Jupiter sell
- [ ] PnL calculation and logging

---

## Stage 5: Production Hardening

- [ ] Circuit breakers (pause on repeated failures)
- [ ] Prometheus metrics export
- [ ] Alerting (Telegram/Discord notifications)
- [ ] Rate limiting and backpressure
- [ ] Mainnet deployment with monitoring

---

## Future Expansions

- Raydium LaunchLab support
- Moonshot integration
- ML-based token scoring
- MEV bundle submission (Jito)
- Multi-wallet orchestration