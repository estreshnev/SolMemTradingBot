# Claude Memory

Persistent context for Claude Code sessions. Update this file when important decisions are made or patterns established.

## Project Context

- **Type**: Solana memecoin trading bot (Pump.fun sniper)
- **Language**: Python 3.12 with strict typing
- **User**: Building production-grade bot, expects reliability and safety

## Active Decisions

- Config-driven: All thresholds/behavior in YAML/JSON, never hardcoded
- Three modes: `dry-run` (log only) → `devnet` (test transactions) → `mainnet` (real trades)
- Idempotency via `tx_signature` to handle duplicate webhooks
- Multiple RPC endpoints with failover for reliability
- **Secrets in .env only**: All API keys, private keys, RPC URLs with keys → `.env` file (gitignored). Use `BOT_` prefix. Never hardcode or commit secrets.

## Code Style

- async/await everywhere (no blocking calls)
- Pydantic models for all data structures
- structlog with JSON output for all logging
- Type hints required on all functions
- Docstrings for public functions only

## Current Focus

**Stage 1.5: Paper Trading Signals**
- Capturing buy signals from live Pump.fun events
- Tracking simulated PnL for strategy validation
- Tuning filter parameters based on real data

## Architecture Notes

**Single-instance design**: This bot is for personal use only. No need for horizontal scaling, distributed state, or complex orchestration. SQLite is fine for signal storage. If scaling becomes needed later, refactor to Postgres/Redis.

## Session Notes

### 2026-01-25: Price Calculation + Restart Resilience

**Price calculation from swap data:**
- Helius `events` field is empty `{}` - no direct price info
- Calculate from tokenTransfers + nativeTransfers:
  ```
  token_price = SOL_amount / token_amount
  market_cap = token_price * 1,000,000,000  (Pump.fun total supply)
  ```
- Added `token_price_sol` and `token_amount` to CurveProgressEvent
- Signal generator uses price for entry tracking

**Restart resilience:**
- `SignalGenerator._load_signaled_tokens()` loads from DB on startup
- Prevents duplicate signals after server restart
- Loads last 24h signals (configurable)

**Live testing results:**
- 400+ signals captured from real Pump.fun activity
- Price and market cap correctly calculated
- Signals persist across restarts

---

### 2026-01-25: Signals Module + Live Helius Integration

**Added signals module for paper trading:**
```
src/signals/
├── models.py    - Signal, SignalStatus, SignalOutcome
├── storage.py   - SQLite persistence with stats queries
├── generator.py - Evaluates events → creates buy signals
└── tracker.py   - Updates signals on migrations, tracks PnL
```

**Fixed Helius webhook integration:**
- Helius sends raw list `[{tx}, {tx}]`, not `{webhookID, transactions}`
- Updated server to normalize both formats
- Parser now extracts token address from `tokenTransfers` and `accountData`
- Filters by `source: PUMP_FUN` to only process relevant transactions

**Helius enhanced transaction format:**
- `type`: SWAP, CREATE, UNKNOWN, WITHDRAW
- `source`: PUMP_FUN
- `signature`, `slot`, `timestamp`
- `tokenTransfers`, `nativeTransfers`, `accountData`

**Live testing verified:**
- ngrok tunnel → Helius webhook → signals DB
- 250+ signals captured from real Pump.fun activity
- Events: curve_progress (swaps), token_created

**API endpoints added:**
- `GET /signals/stats` - win rate, avg PnL, counts by status
- `GET /signals/recent` - recent signals with outcomes

### 2025-01-24: Initial Scaffolding Complete

**Created structure:**
```
src/
├── config/settings.py    - Pydantic Settings with YAML support
├── models/events.py      - Event types (TokenCreated, CurveProgress, Migration)
├── webhook/
│   ├── server.py         - FastAPI app with /webhook and /health
│   ├── parser.py         - Helius payload → events
│   └── idempotency.py    - LRU-based tx_sig deduplication
├── filters/base.py       - FilterChain pattern for extensibility
└── utils/logging.py      - structlog setup
```