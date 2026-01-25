"""SQLite storage for signals."""

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import structlog

from src.signals.models import Signal, SignalOutcome, SignalStatus

logger = structlog.get_logger()


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


def decimal_decoder(dct: dict[str, Any]) -> dict[str, Any]:
    """Decode decimal strings back to Decimal objects."""
    decimal_fields = {
        "entry_liquidity_sol",
        "entry_market_cap_sol",
        "entry_price_sol",
        "simulated_buy_sol",
        "simulated_entry_sol",
        "simulated_exit_sol",
        "simulated_pnl_sol",
        "price_at_migration",
    }
    for key, value in dct.items():
        if key in decimal_fields and value is not None:
            dct[key] = Decimal(value)
    return dct


class SignalStorage:
    """SQLite-based signal storage for paper trading analysis."""

    def __init__(self, db_path: Path | str = "data/signals.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY,
                    token_address TEXT NOT NULL,
                    token_name TEXT,
                    token_symbol TEXT,
                    creator_address TEXT,
                    trigger_tx_signature TEXT NOT NULL,
                    signal_time TEXT NOT NULL,
                    entry_curve_progress_pct REAL NOT NULL,
                    entry_liquidity_sol TEXT NOT NULL,
                    entry_market_cap_sol TEXT,
                    entry_price_sol TEXT,
                    dev_holds_pct REAL,
                    simulated_buy_sol TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    outcome_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_token
                ON signals(token_address)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_status
                ON signals(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_time
                ON signals(signal_time)
            """)

            conn.commit()
            logger.info("signal_storage_initialized", db_path=str(self.db_path))

    def save(self, signal: Signal) -> None:
        """Save or update a signal."""
        outcome_json = json.dumps(
            signal.outcome.model_dump(mode="json"),
            cls=DecimalEncoder,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO signals (
                    id, token_address, token_name, token_symbol, creator_address,
                    trigger_tx_signature, signal_time, entry_curve_progress_pct,
                    entry_liquidity_sol, entry_market_cap_sol, entry_price_sol,
                    dev_holds_pct, simulated_buy_sol, status, outcome_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    signal.id,
                    signal.token_address,
                    signal.token_name,
                    signal.token_symbol,
                    signal.creator_address,
                    signal.trigger_tx_signature,
                    signal.signal_time.isoformat(),
                    signal.entry_curve_progress_pct,
                    str(signal.entry_liquidity_sol),
                    str(signal.entry_market_cap_sol) if signal.entry_market_cap_sol else None,
                    str(signal.entry_price_sol) if signal.entry_price_sol else None,
                    signal.dev_holds_pct,
                    str(signal.simulated_buy_sol),
                    signal.status.value,
                    outcome_json,
                    signal.created_at.isoformat(),
                    signal.updated_at.isoformat(),
                ),
            )
            conn.commit()

        logger.debug(
            "signal_saved",
            signal_id=signal.id,
            token=signal.token_address,
            status=signal.status.value,
        )

    def get(self, signal_id: str) -> Signal | None:
        """Get a signal by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM signals WHERE id = ?",
                (signal_id,),
            ).fetchone()

        return self._row_to_signal(row) if row else None

    def get_by_token(self, token_address: str) -> list[Signal]:
        """Get all signals for a token."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM signals WHERE token_address = ? ORDER BY signal_time DESC",
                (token_address,),
            ).fetchall()

        return [self._row_to_signal(row) for row in rows]

    def get_pending(self, limit: int = 100) -> list[Signal]:
        """Get pending signals awaiting outcome."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM signals
                WHERE status = ?
                ORDER BY signal_time ASC
                LIMIT ?
            """,
                (SignalStatus.PENDING.value, limit),
            ).fetchall()

        return [self._row_to_signal(row) for row in rows]

    def get_recent(self, hours: int = 24, limit: int = 100) -> list[Signal]:
        """Get recent signals within the specified hours."""
        cutoff = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM signals
                WHERE signal_time >= datetime(?, '-' || ? || ' hours')
                ORDER BY signal_time DESC
                LIMIT ?
            """,
                (cutoff, hours, limit),
            ).fetchall()

        return [self._row_to_signal(row) for row in rows]

    def update_status(self, signal_id: str, status: SignalStatus) -> None:
        """Update signal status."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE signals
                SET status = ?, updated_at = ?
                WHERE id = ?
            """,
                (status.value, datetime.utcnow().isoformat(), signal_id),
            )
            conn.commit()

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics for analysis."""
        with self._get_connection() as conn:
            # Total counts by status
            status_counts = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM signals
                GROUP BY status
            """).fetchall()

            # PnL stats for completed signals
            pnl_stats = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(json_extract(outcome_json, '$.simulated_pnl_pct')) as avg_pnl_pct,
                    MIN(json_extract(outcome_json, '$.simulated_pnl_pct')) as min_pnl_pct,
                    MAX(json_extract(outcome_json, '$.simulated_pnl_pct')) as max_pnl_pct,
                    SUM(CASE WHEN json_extract(outcome_json, '$.simulated_pnl_pct') > 0 THEN 1 ELSE 0 END) as winners,
                    SUM(CASE WHEN json_extract(outcome_json, '$.simulated_pnl_pct') <= 0 THEN 1 ELSE 0 END) as losers
                FROM signals
                WHERE status = 'migrated'
                AND json_extract(outcome_json, '$.simulated_pnl_pct') IS NOT NULL
            """).fetchone()

        return {
            "by_status": {row["status"]: row["count"] for row in status_counts},
            "pnl": {
                "total_completed": pnl_stats["total"] or 0,
                "avg_pnl_pct": pnl_stats["avg_pnl_pct"],
                "min_pnl_pct": pnl_stats["min_pnl_pct"],
                "max_pnl_pct": pnl_stats["max_pnl_pct"],
                "winners": pnl_stats["winners"] or 0,
                "losers": pnl_stats["losers"] or 0,
                "win_rate": (
                    pnl_stats["winners"] / pnl_stats["total"] * 100
                    if pnl_stats["total"]
                    else None
                ),
            },
        }

    def _row_to_signal(self, row: sqlite3.Row) -> Signal:
        """Convert a database row to a Signal model."""
        outcome_data = json.loads(row["outcome_json"] or "{}", object_hook=decimal_decoder)

        return Signal(
            id=row["id"],
            token_address=row["token_address"],
            token_name=row["token_name"],
            token_symbol=row["token_symbol"],
            creator_address=row["creator_address"],
            trigger_tx_signature=row["trigger_tx_signature"],
            signal_time=datetime.fromisoformat(row["signal_time"]),
            entry_curve_progress_pct=row["entry_curve_progress_pct"],
            entry_liquidity_sol=Decimal(row["entry_liquidity_sol"]),
            entry_market_cap_sol=(
                Decimal(row["entry_market_cap_sol"]) if row["entry_market_cap_sol"] else None
            ),
            entry_price_sol=Decimal(row["entry_price_sol"]) if row["entry_price_sol"] else None,
            dev_holds_pct=row["dev_holds_pct"],
            simulated_buy_sol=Decimal(row["simulated_buy_sol"]),
            status=SignalStatus(row["status"]),
            outcome=SignalOutcome(**outcome_data),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )