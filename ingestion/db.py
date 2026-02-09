"""Safe DuckDB connection management for the ingestion pipeline.

Guarantees:
- Connections are always closed, even on crash
- Writes happen in explicit transactions (no half-written state)
- CHECKPOINT after writes to flush WAL to disk
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import duckdb

from config import DB_PATH

log = logging.getLogger(__name__)


@contextmanager
def get_conn(read_only: bool = False) -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager that guarantees connection cleanup.

    Usage:
        with get_conn() as conn:
            conn.execute("INSERT ...")
    """
    conn = duckdb.connect(str(DB_PATH), read_only=read_only)
    try:
        yield conn
    finally:
        if not read_only:
            try:
                conn.execute("CHECKPOINT")
            except Exception:
                pass  # Best-effort flush
        conn.close()


@contextmanager
def transaction(conn: duckdb.DuckDBPyConnection) -> Generator[None, None, None]:
    """Explicit transaction with rollback on error.

    Usage:
        with get_conn() as conn:
            with transaction(conn):
                conn.execute("INSERT ...")
                conn.execute("INSERT ...")
            # auto-committed here
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        yield
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def batch_execute(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    rows: list[list],
    batch_size: int = 1000,
) -> int:
    """Execute a parameterized INSERT in batched transactions.

    If the process crashes mid-way, only the current batch is lost.
    All previously committed batches are safe on disk.

    Returns the total number of rows inserted.
    """
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        with transaction(conn):
            conn.executemany(sql, batch)
        total += len(batch)
    return total
