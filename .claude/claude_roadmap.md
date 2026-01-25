# Project Roadmap

## Project Pivot Notice

**Original**: Pump.fun sniper bot
**New Direction**: Raydium signal bot with ML scoring

---

## Stage 1: Core Infrastructure ✅ COMPLETE

**Goal**: Basic webhook processing and project structure

- [x] Project scaffolding (pyproject.toml, src/ structure, Docker)
- [x] Config system (Pydantic Settings, YAML loading)
- [x] Webhook server (FastAPI POST /webhook endpoint)
- [x] Helius payload parser (enhanced transaction format)
- [x] Idempotency layer (tx_signature deduplication)
- [x] Structured logging (structlog JSON)
- [x] Test suite (pytest)
- [x] CLI tools (view_signals.py, setup_helius_webhook.py)

---

## Stage 2: Raydium Pool Detection ← CURRENT

**Goal**: Detect new Raydium pool creations via Helius webhook

- [ ] Update Helius webhook to monitor Raydium program
- [ ] Detect pool creation events (LP mint, initial liquidity)
- [ ] Extract token pair info (base token, quote token)
- [ ] Extract pool address and initial liquidity
- [ ] Store detected pools in SQLite

**Raydium Programs**:
- AMM: `675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8`
- CLMM: `CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK`

---

## Stage 3: Data Enrichment

**Goal**: Fetch additional data from external sources

- [ ] Dexscreener API integration
  - [ ] Get market cap (MC)
  - [ ] Get 24h volume
  - [ ] Get pool age
  - [ ] Get price and liquidity
- [ ] RPC holder analysis
  - [ ] Fetch top token holders
  - [ ] Calculate top 10 holders percentage
  - [ ] Detect concentrated holdings

---

## Stage 4: Filtering & Scoring

**Goal**: Filter signals and calculate quality score

- [ ] Configurable filter thresholds:
  - [ ] MC > $10,000
  - [ ] Volume > $5,000
  - [ ] Top 10 holders < 30%
- [ ] Basic scoring system (weighted factors)
- [ ] Score persistence for ML training data

---

## Stage 5: Telegram Notifications

**Goal**: Send filtered signals to Telegram

- [ ] Telegram bot integration (python-telegram-bot)
- [ ] Signal message formatting
  - [ ] Token name/symbol
  - [ ] Contract address
  - [ ] MC, Volume, Age
  - [ ] Top holders %
  - [ ] Score
  - [ ] Dexscreener link
- [ ] Rate limiting (avoid spam)
- [ ] Error handling and retries

---

## Stage 6: ML Scoring (Future)

**Goal**: Machine learning based signal scoring

- [ ] Data collection pipeline
- [ ] Feature engineering
- [ ] Model training (outcome prediction)
- [ ] Model serving integration
- [ ] A/B testing framework

---

## Future Expansions

- Multi-DEX support (Orca, Meteora)
- Social signals (Twitter, Telegram mentions)
- Wallet tracking (smart money follows)
- Auto-trading integration
- Dashboard/UI for signal review