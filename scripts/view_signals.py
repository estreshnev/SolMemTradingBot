#!/usr/bin/env python3
"""View signals from the database.

Usage:
    python scripts/view_signals.py              # Show stats + recent 10
    python scripts/view_signals.py --all        # Show all signals
    python scripts/view_signals.py --recent 20  # Show recent 20
    python scripts/view_signals.py --migrated   # Show migrated only
    python scripts/view_signals.py --with-price # Show signals with price data
    python scripts/view_signals.py --token ABC  # Search by token address
"""

import argparse
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "signals.db"


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the server first to create the database.")
        exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def show_stats(conn: sqlite3.Connection) -> None:
    print("=" * 70)
    print("SIGNAL STATISTICS")
    print("=" * 70)

    cur = conn.cursor()

    # Total count
    cur.execute("SELECT COUNT(*) FROM signals")
    total = cur.fetchone()[0]

    # With price
    cur.execute("SELECT COUNT(*) FROM signals WHERE entry_price_sol IS NOT NULL")
    with_price = cur.fetchone()[0]

    # By status
    cur.execute("SELECT status, COUNT(*) as cnt FROM signals GROUP BY status")
    status_counts = {row["status"]: row["cnt"] for row in cur.fetchall()}

    # PnL stats
    cur.execute("""
        SELECT
            AVG(json_extract(outcome_json, '$.simulated_pnl_pct')) as avg_pnl,
            MIN(json_extract(outcome_json, '$.simulated_pnl_pct')) as min_pnl,
            MAX(json_extract(outcome_json, '$.simulated_pnl_pct')) as max_pnl
        FROM signals
        WHERE status = 'migrated'
        AND json_extract(outcome_json, '$.simulated_pnl_pct') IS NOT NULL
    """)
    pnl = cur.fetchone()

    print(f"Total signals:     {total}")
    print(f"With price data:   {with_price}")
    print(f"Without price:     {total - with_price}")
    print()
    print("By Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status:15} {count:>6}")
    print()

    if pnl["avg_pnl"] is not None:
        print("PnL (migrated signals):")
        print(f"  Average: {pnl['avg_pnl']:.2f}%")
        print(f"  Min:     {pnl['min_pnl']:.2f}%")
        print(f"  Max:     {pnl['max_pnl']:.2f}%")
    print()


def format_signal(row: sqlite3.Row) -> str:
    outcome = json.loads(row["outcome_json"]) if row["outcome_json"] else {}
    pnl = outcome.get("simulated_pnl_pct")
    pnl_str = f"{pnl:+.1f}%" if pnl is not None else "N/A"

    price = float(row["entry_price_sol"]) if row["entry_price_sol"] else None
    price_str = f"{price:.10f}" if price else "N/A"

    mcap = float(row["entry_market_cap_sol"]) if row["entry_market_cap_sol"] else None
    mcap_str = f"{mcap:.2f}" if mcap else "N/A"

    liq = float(row["entry_liquidity_sol"]) if row["entry_liquidity_sol"] else 0

    lines = [
        f"Token:      {row['token_address']}",
        f"Status:     {row['status']:10}  PnL: {pnl_str}",
        f"Price:      {price_str} SOL/token",
        f"Market Cap: {mcap_str} SOL",
        f"Liquidity:  {liq:.6f} SOL",
        f"Created:    {row['created_at']}",
        f"TX:         {row['trigger_tx_signature'][:50]}...",
    ]
    return "\n".join(lines)


def show_signals(conn: sqlite3.Connection, query: str, params: tuple = ()) -> None:
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        print("No signals found.")
        return

    print(f"Found {len(rows)} signal(s):")
    print("-" * 70)

    for row in rows:
        print(format_signal(row))
        print("-" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="View signals from database")
    parser.add_argument("--all", action="store_true", help="Show all signals")
    parser.add_argument("--recent", type=int, metavar="N", help="Show recent N signals")
    parser.add_argument("--migrated", action="store_true", help="Show migrated signals only")
    parser.add_argument("--pending", action="store_true", help="Show pending signals only")
    parser.add_argument("--with-price", action="store_true", help="Show signals with price data")
    parser.add_argument("--token", type=str, metavar="ADDR", help="Search by token address")
    parser.add_argument("--no-stats", action="store_true", help="Skip statistics")
    args = parser.parse_args()

    conn = get_connection()

    # Show stats unless disabled
    if not args.no_stats:
        show_stats(conn)

    # Build query based on args
    if args.token:
        query = "SELECT * FROM signals WHERE token_address LIKE ? ORDER BY created_at DESC"
        params = (f"%{args.token}%",)
    elif args.migrated:
        query = "SELECT * FROM signals WHERE status = 'migrated' ORDER BY created_at DESC"
        params = ()
    elif args.pending:
        query = "SELECT * FROM signals WHERE status = 'pending' ORDER BY created_at DESC LIMIT 20"
        params = ()
    elif args.with_price:
        query = "SELECT * FROM signals WHERE entry_price_sol IS NOT NULL ORDER BY created_at DESC"
        params = ()
    elif args.all:
        query = "SELECT * FROM signals ORDER BY created_at DESC"
        params = ()
    else:
        # Default: recent 10
        limit = args.recent or 10
        query = f"SELECT * FROM signals ORDER BY created_at DESC LIMIT {limit}"
        params = ()

    show_signals(conn, query, params)


if __name__ == "__main__":
    main()