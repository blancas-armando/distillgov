"""DuckDB database connection for the API."""

from __future__ import annotations

import duckdb
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH


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


def escape_like(value: str) -> str:
    """Escape special ILIKE characters (%, _, \\) in user input."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
