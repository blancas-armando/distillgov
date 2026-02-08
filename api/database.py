"""DuckDB database connection for the API."""

from __future__ import annotations

import duckdb
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

DB_PATH = Path(__file__).parent.parent / "db" / "distillgov.duckdb"


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a read-only database connection."""
    return duckdb.connect(str(DB_PATH), read_only=True)


@contextmanager
def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
