"""Sync members from Congress.gov API to DuckDB."""

import duckdb
from pathlib import Path
from rich.console import Console
from rich.progress import track

from ingestion.client import CongressClient

console = Console()
DB_PATH = Path(__file__).parent.parent / "db" / "distillgov.duckdb"


def sync_members(congress: int = 118):
    """Sync all members from a Congress into DuckDB."""
    console.print(f"Fetching members from Congress {congress}...")

    with CongressClient() as client:
        members = []

        # Fetch both chambers
        for chamber in ["house", "senate"]:
            console.print(f"  Fetching {chamber}...")
            offset = 0

            while True:
                response = client.get_members(congress=congress, chamber=chamber, offset=offset)
                batch = response.get("members", [])

                if not batch:
                    break

                members.extend(batch)
                offset += len(batch)

                if offset >= response.get("pagination", {}).get("count", 0):
                    break

        console.print(f"Fetched {len(members)} members")

    # Transform and load into DuckDB
    conn = duckdb.connect(str(DB_PATH))

    inserted = 0
    for member in track(members, description="Loading members..."):
        # Extract fields from API response
        bioguide_id = member.get("bioguideId")
        if not bioguide_id:
            continue

        # Parse name
        name = member.get("name", "")
        parts = name.split(", ") if ", " in name else [name, ""]
        last_name = parts[0] if parts else ""
        first_name = parts[1].split()[0] if len(parts) > 1 and parts[1] else ""

        # Determine chamber from terms or district
        terms = member.get("terms", {}).get("item", [])
        latest_term = terms[-1] if terms else {}
        chamber = latest_term.get("chamber", "").lower()
        if not chamber:
            chamber = "house" if member.get("district") else "senate"

        # Get district (House only)
        district = member.get("district")
        if district == 0:  # At-large
            district = 0

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
                member.get("name"),
                member.get("partyName", "")[:1],  # First letter: D, R, I
                member.get("state"),
                district,
                chamber,
                True,  # Current members
                member.get("depiction", {}).get("imageUrl"),
                member.get("officialWebsiteUrl"),
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} members[/green]")


if __name__ == "__main__":
    sync_members()
