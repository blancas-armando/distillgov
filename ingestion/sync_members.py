"""Sync members from Congress.gov API to DuckDB."""

from __future__ import annotations

import logging

from rich.progress import track

from ingestion.client import CongressClient
from ingestion.constants import normalize_state
from ingestion.db import batch_execute, get_conn
from ingestion.sync_meta import set_last_sync

log = logging.getLogger(__name__)

INSERT_SQL = """
    INSERT OR REPLACE INTO members (
        bioguide_id, first_name, last_name, full_name,
        party, state, district, chamber, is_current,
        image_url, official_url, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
"""


def _transform_member(member: dict) -> list | None:
    """Transform a raw API member dict into an insert row, or None if invalid."""
    bioguide_id = member.get("bioguideId")
    if not bioguide_id:
        return None

    # Parse name (format: "Last, First Middle")
    name = member.get("name", "")
    parts = name.split(", ") if ", " in name else [name, ""]
    last_name = parts[0] if parts else ""
    first_name = parts[1].split()[0] if len(parts) > 1 and parts[1] else ""

    # Determine chamber from terms
    terms = member.get("terms", {}).get("item", [])
    latest_term = terms[-1] if terms else {}
    chamber_raw = latest_term.get("chamber", "")

    if "house" in chamber_raw.lower():
        chamber = "house"
    elif "senate" in chamber_raw.lower():
        chamber = "senate"
    else:
        # Fallback: if has district, it's house
        chamber = "house" if member.get("district") else "senate"

    # District (House only, 0 = at-large)
    district = member.get("district")

    # Party first letter
    party_name = member.get("partyName", "")
    party = party_name[0] if party_name else None

    return [
        bioguide_id,
        first_name,
        last_name,
        name,
        party,
        normalize_state(member.get("state")),
        district,
        chamber,
        True,
        f"https://unitedstates.github.io/images/congress/450x550/{bioguide_id}.jpg",
        member.get("officialWebsiteUrl"),
    ]


def sync_members(congress: int = 118):
    """Sync all current members into DuckDB."""
    log.info("Fetching current members of Congress...")

    with CongressClient() as client:
        members = []
        offset = 0

        while True:
            response = client.get_members(current_member=True, offset=offset)
            batch = response.get("members", [])

            if not batch:
                break

            members.extend(batch)
            offset += len(batch)
            log.info("  Fetched %d members...", len(members))

            if offset >= response.get("pagination", {}).get("count", 0):
                break

        log.info("Total: %d current members", len(members))

    # Transform rows, filtering out members without a bioguide_id
    rows = []
    for member in track(members, description="Loading members..."):
        row = _transform_member(member)
        if row is not None:
            rows.append(row)

    with get_conn() as conn:
        inserted = batch_execute(conn, INSERT_SQL, rows)

    log.info("Inserted %d members", inserted)
    set_last_sync("members", inserted)


if __name__ == "__main__":
    sync_members()
