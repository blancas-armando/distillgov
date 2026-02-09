"""Track sync timestamps for incremental fetching."""

from __future__ import annotations

from datetime import datetime, timezone

from ingestion.db import get_conn


def get_last_sync(entity: str) -> str | None:
    """Get the fromDateTime value for an incremental sync.

    Returns an ISO timestamp string like "2025-01-15T00:00:00Z",
    or None if this entity has never been synced (triggering a full fetch).
    """
    try:
        with get_conn(read_only=True) as conn:
            row = conn.execute(
                "SELECT last_update_dt FROM sync_meta WHERE entity = ?",
                [entity],
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None


def set_last_sync(entity: str, record_count: int = 0) -> None:
    """Record that a sync just completed.

    Sets last_update_dt to now (UTC) so the next run can use it as fromDateTime.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sync_meta (entity, last_sync_at, last_update_dt, record_count)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?)
            """,
            [entity, now, record_count],
        )
