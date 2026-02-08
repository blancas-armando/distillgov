"""Sync bills from Congress.gov API to DuckDB."""

from __future__ import annotations

import duckdb
from pathlib import Path
from rich.console import Console
from rich.progress import track

from ingestion.client import CongressClient

console = Console()
DB_PATH = Path(__file__).parent.parent / "db" / "distillgov.duckdb"

# Bill types to sync
BILL_TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]


def sync_bills(congress: int = 118, bill_types: list[str] | None = None):
    """Sync bills from a Congress into DuckDB."""
    bill_types = bill_types or BILL_TYPES
    console.print(f"Fetching bills from Congress {congress}...")

    with CongressClient() as client:
        bills = []

        for bill_type in bill_types:
            console.print(f"  Fetching {bill_type.upper()}...")
            offset = 0

            while True:
                response = client.get_bills(congress=congress, bill_type=bill_type, offset=offset)
                batch = response.get("bills", [])

                if not batch:
                    break

                bills.extend(batch)
                offset += len(batch)

                # Limit for initial sync (remove for full sync)
                if offset >= 500:
                    console.print(f"    [dim]Limited to 500 {bill_type.upper()} bills[/dim]")
                    break

                if offset >= response.get("pagination", {}).get("count", 0):
                    break

        console.print(f"Fetched {len(bills)} bills")

    # Transform and load into DuckDB
    conn = duckdb.connect(str(DB_PATH))

    inserted = 0
    for bill in track(bills, description="Loading bills..."):
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number")

        if not bill_number:
            continue

        bill_id = f"{congress}-{bill_type}-{bill_number}"

        # Get latest action
        latest_action = bill.get("latestAction", {})
        latest_action_text = latest_action.get("text")
        latest_action_date = latest_action.get("actionDate")

        # Determine status from latest action
        status = determine_status(latest_action_text)

        conn.execute(
            """
            INSERT OR REPLACE INTO bills (
                bill_id, congress, bill_type, bill_number,
                title, introduced_date, origin_chamber,
                latest_action, latest_action_date, status,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                bill_id,
                congress,
                bill_type,
                bill_number,
                bill.get("title"),
                bill.get("introducedDate"),
                bill.get("originChamber"),
                latest_action_text,
                latest_action_date,
                status,
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} bills[/green]")


def determine_status(action_text: str | None) -> str:
    """Determine bill status from latest action text."""
    if not action_text:
        return "introduced"

    action_lower = action_text.lower()

    if "became public law" in action_lower or "signed by president" in action_lower:
        return "enacted"
    elif "vetoed" in action_lower:
        return "vetoed"
    elif "passed senate" in action_lower and "passed house" in action_lower:
        return "passed_both"
    elif "passed senate" in action_lower:
        return "passed_senate"
    elif "passed house" in action_lower:
        return "passed_house"
    elif "referred to" in action_lower and "committee" in action_lower:
        return "in_committee"
    else:
        return "introduced"


if __name__ == "__main__":
    sync_bills()
