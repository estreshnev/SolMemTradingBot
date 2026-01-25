# Project Roadmap

## Stage 1: Helius Webhook Integration ✅ COMPLETE

**Goal**: Receive and process Pump.fun events reliably

- [x] Project scaffolding (pyproject.toml, src/ structure, Docker)
- [x] Config system (Pydantic Settings, YAML loading)
- [x] Webhook server (FastAPI POST /webhook endpoint)
- [x] Helius payload parser → structured events (real Helius format implemented)
- [x] Event models (TokenCreated, CurveProgress, Migration)
- [x] Basic filters (liquidity, dev holds, curve progress thresholds)
- [x] Idempotency layer (tx_signature deduplication)
- [x] Structured logging (structlog JSON)
- [x] Test suite (pytest, basic webhook tests)
- [x] Local testing (ngrok + mainnet Pump.fun events)

**Deliverable**: Bot logs all Pump.fun events with filtering applied

---

## Stage 1.5: Paper Trading Signals ← CURRENT

**Goal**: Capture buy signals and track simulated PnL to validate strategy before real trading

- [x] Signal models (Signal, SignalStatus, SignalOutcome)
- [x] SQLite storage layer for signal persistence
- [x] Signal generator (evaluates events against filters → generates buy signals)
- [x] Outcome tracker (updates signals with migration/price data, calculates PnL)
- [x] Integration with webhook handler (automatic signal processing)
- [x] Config section for signals (enabled, db_path, simulated_buy_sol, expiry_hours)
- [x] API endpoints for analysis (/signals/stats, /signals/recent)
- [ ] Price polling for pending signals (periodic curve progress checks)
- [ ] Analysis scripts/notebook for reviewing signal performance
- [ ] Parameter optimization based on collected data

**Deliverable**: Bot captures all trade signals, tracks outcomes, provides PnL analysis for strategy tuning

**Endpoints**:
- `GET /signals/stats` - Aggregate statistics (win rate, avg PnL, counts by status)
- `GET /signals/recent?hours=24&limit=50` - Recent signals with outcomes

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