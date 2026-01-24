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

**Stage 1: Helius Webhook Integration**
- Webhook endpoint receiving Pump.fun events
- Event parsing and validation
- Config-driven filtering
- Comprehensive logging

## Session Notes

### 2025-01-24: Initial Scaffolding Complete

**Created structure:**
```
src/
├── config/settings.py    - Pydantic Settings with YAML support
├── models/events.py      - Event types (TokenCreated, CurveProgress, Migration)
├── webhook/
│   ├── server.py         - FastAPI app with /webhook and /health
│   ├── parser.py         - Helius payload → events (placeholder logic)
│   └── idempotency.py    - LRU-based tx_sig deduplication
├── filters/base.py       - FilterChain pattern for extensibility
└── utils/logging.py      - structlog setup
```

**Next steps:**
1. Implement real Helius payload parsing (need sample payloads)
2. Add config-driven filters (min_liquidity, max_dev_holds, etc.)
3. Test with ngrok + real Helius webhooks