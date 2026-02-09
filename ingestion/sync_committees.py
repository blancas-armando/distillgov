"""Sync committee membership from Congress.gov API to DuckDB."""

from __future__ import annotations

import duckdb
from rich.console import Console
from rich.progress import track

from config import DB_PATH
from ingestion.client import CongressClient

console = Console()


def sync_committees(congress: int = 118):
    """Sync committees and their members from Congress.gov.

    Fetches the committee list, then fetches membership for each committee.
    """
    console.print(f"Fetching committees for Congress {congress}...")

    with CongressClient() as client:
        committees: list[dict] = []
        offset = 0

        while True:
            response = client.get_committees(congress=congress, offset=offset)
            batch = response.get("committees", [])

            if not batch:
                break

            committees.extend(batch)
            offset += len(batch)

            if offset >= response.get("pagination", {}).get("count", 0):
                break

        console.print(f"Found {len(committees)} committees")

    if not committees:
        return

    conn = duckdb.connect(str(DB_PATH))

    committees_inserted = 0
    members_inserted = 0

    with CongressClient() as client:
        for committee in track(committees, description="Loading committees..."):
            name = committee.get("name", "")
            chamber = committee.get("chamber", "")
            committee_type = committee.get("committeeTypeCode", "")
            parent = committee.get("parent")
            parent_id = parent.get("systemCode") if parent else None
            url = committee.get("url")

            # systemCode is the committee identifier (e.g., "hsag00")
            system_code = committee.get("systemCode", "")
            if not system_code:
                continue

            conn.execute(
                """
                INSERT OR REPLACE INTO committees (
                    committee_id, name, chamber, committee_type, parent_id, url
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [system_code, name, chamber.lower() if chamber else None,
                 committee_type, parent_id, url]
            )
            committees_inserted += 1

            # Fetch committee detail which may include current members
            # The committee list response might include a subcommittees field
            # but not members — we need the detail endpoint
            try:
                chamber_code = chamber.lower() if chamber else "house"
                # Extract the base code (e.g., "hsag" from "hsag00")
                detail = client.get_committee(congress, chamber_code, system_code)
                committee_data = detail.get("committee", {})

                # Check for committee membership in the response
                # Congress.gov might return members under "committeeBills" or
                # we may need to look at a different structure
                # The detail response structure varies — extract what we can
                current_members = committee_data.get("currentMembers", [])
                if not current_members:
                    # Some responses nest under "subcommittees" etc.
                    current_members = committee_data.get("members", [])

                for member in current_members:
                    bioguide_id = member.get("bioguideId")
                    if not bioguide_id:
                        continue

                    role = member.get("role") or "Member"

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO committee_members (
                            committee_id, bioguide_id, role
                        ) VALUES (?, ?, ?)
                        """,
                        [system_code, bioguide_id, role]
                    )
                    members_inserted += 1

            except Exception as e:
                console.print(f"[dim]  {system_code}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Inserted {committees_inserted} committees, {members_inserted} memberships[/green]")
