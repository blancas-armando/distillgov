"""Sync members from Congress.gov API to DuckDB."""

from __future__ import annotations

import duckdb
from rich.console import Console
from rich.progress import track

from config import DB_PATH
from ingestion.client import CongressClient
from ingestion.constants import normalize_state

console = Console()


def sync_members(congress: int = 118):
    """Sync all current members into DuckDB."""
    console.print("Fetching current members of Congress...")

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
            console.print(f"  Fetched {len(members)} members...")

            if offset >= response.get("pagination", {}).get("count", 0):
                break

        console.print(f"Total: {len(members)} current members")

    # Transform and load into DuckDB
    conn = duckdb.connect(str(DB_PATH))

    inserted = 0
    for member in track(members, description="Loading members..."):
        bioguide_id = member.get("bioguideId")
        if not bioguide_id:
            continue

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

        conn.execute(
            """
            INSERT OR REPLACE INTO members (
                bioguide_id, first_name, last_name, full_name,
                party, state, district, chamber, is_current,
                image_url, official_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
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
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} members[/green]")


if __name__ == "__main__":
    sync_members()
