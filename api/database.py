"""DuckDB database connection for the API."""

from __future__ import annotations

import duckdb
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH


_conn: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a shared read-only database connection (singleton)."""
    global _conn
    if _conn is None:
        _conn = duckdb.connect(str(DB_PATH), read_only=True)
    return _conn


@contextmanager
def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Context manager for the shared database connection."""
    yield get_connection()


def escape_like(value: str) -> str:
    """Escape special ILIKE characters (%, _, \\) in user input."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


PASSAGE_VOTE_FILTER = (
    "(question ILIKE '%passage%' OR question ILIKE '%pass%' "
    "OR question ILIKE '%conference report%' OR question ILIKE '%override%' "
    "OR question ILIKE '%concur%' OR question ILIKE '%adopt%' "
    "OR question ILIKE '%ratif%')"
)
