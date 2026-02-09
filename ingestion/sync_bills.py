"""Sync bills from Congress.gov API to DuckDB."""

from __future__ import annotations

import re

import duckdb
from rich.console import Console
from rich.progress import track

from config import DB_PATH
from ingestion.client import CongressClient

console = Console()

# Bill types to sync
BILL_TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]


def sync_bills(congress: int = 118, bill_types: list[str] | None = None, with_details: bool = False):
    """Sync bills from a Congress into DuckDB.

    Args:
        congress: Congress number (e.g., 118)
        bill_types: List of bill types to sync (default: all)
        with_details: If True, fetch cosponsors and actions for each bill (slower)
    """
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

        # Policy area from list endpoint
        policy_area = bill.get("policyArea", {}).get("name") if bill.get("policyArea") else None

        conn.execute(
            """
            INSERT OR REPLACE INTO bills (
                bill_id, congress, bill_type, bill_number,
                title, introduced_date, origin_chamber,
                latest_action, latest_action_date, status,
                policy_area, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                policy_area,
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} bills[/green]")

    if with_details:
        sync_bill_details(congress, bills)


def sync_bill_details(congress: int, bills: list[dict]):
    """Sync cosponsors and actions for bills."""
    console.print(f"\n[blue]Fetching cosponsors and actions for {len(bills)} bills...[/blue]")

    conn = duckdb.connect(str(DB_PATH))

    cosponsors_inserted = 0
    actions_inserted = 0
    sponsors_updated = 0

    with CongressClient() as client:
        for bill in track(bills, description="Fetching bill details..."):
            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number")

            if not bill_number:
                continue

            bill_id = f"{congress}-{bill_type}-{bill_number}"

            try:
                # Fetch detailed bill info (for sponsor)
                detail = client.get_bill(congress, bill_type, bill_number)
                bill_data = detail.get("bill", {})

                # Update sponsor if available
                sponsors = bill_data.get("sponsors", [])
                if sponsors:
                    sponsor = sponsors[0]
                    sponsor_id = sponsor.get("bioguideId")
                    if sponsor_id:
                        conn.execute(
                            "UPDATE bills SET sponsor_id = ? WHERE bill_id = ?",
                            [sponsor_id, bill_id]
                        )
                        sponsors_updated += 1

                # Fetch and insert cosponsors
                cosponsors_response = client.get_bill_cosponsors(congress, bill_type, bill_number)
                cosponsors = cosponsors_response.get("cosponsors", [])

                for cosponsor in cosponsors:
                    bioguide_id = cosponsor.get("bioguideId")
                    if not bioguide_id:
                        continue

                    cosponsor_date = cosponsor.get("sponsorshipDate")
                    is_original = cosponsor.get("isOriginalCosponsor", False)

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO bill_cosponsors (
                            bill_id, bioguide_id, cosponsor_date, is_original
                        ) VALUES (?, ?, ?, ?)
                        """,
                        [bill_id, bioguide_id, cosponsor_date, is_original]
                    )
                    cosponsors_inserted += 1

                # Fetch and insert actions
                actions_response = client.get_bill_actions(congress, bill_type, bill_number)
                actions = actions_response.get("actions", [])

                for idx, action in enumerate(actions):
                    action_date = action.get("actionDate")
                    action_text = action.get("text")
                    action_type = action.get("type")
                    action_chamber = action.get("actionCode", "")[:1]  # H or S

                    if action_chamber == "H":
                        chamber = "house"
                    elif action_chamber == "S":
                        chamber = "senate"
                    else:
                        chamber = None

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO bill_actions (
                            bill_id, action_date, action_text, action_type, chamber, sequence
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [bill_id, action_date, action_text, action_type, chamber, idx]
                    )
                    actions_inserted += 1

            except Exception as e:
                console.print(f"[dim]  {bill_id}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Updated {sponsors_updated} sponsors[/green]")
    console.print(f"[green]Inserted {cosponsors_inserted} cosponsors[/green]")
    console.print(f"[green]Inserted {actions_inserted} actions[/green]")


def sync_cosponsors(congress: int = 118):
    """Sync cosponsors for all bills in the database."""
    console.print(f"Syncing cosponsors for Congress {congress}...")

    conn = duckdb.connect(str(DB_PATH))
    bills = conn.execute(
        "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
        [congress]
    ).fetchall()
    conn.close()

    if not bills:
        console.print("[yellow]No bills found. Run 'sync bills' first.[/yellow]")
        return

    console.print(f"Found {len(bills)} bills")

    conn = duckdb.connect(str(DB_PATH))
    inserted = 0
    sponsors_updated = 0

    with CongressClient() as client:
        for bill_id, bill_type, bill_number in track(bills, description="Fetching cosponsors..."):
            try:
                # Get detailed bill for sponsor
                detail = client.get_bill(congress, bill_type, bill_number)
                bill_data = detail.get("bill", {})

                sponsors = bill_data.get("sponsors", [])
                if sponsors:
                    sponsor = sponsors[0]
                    sponsor_id = sponsor.get("bioguideId")
                    if sponsor_id:
                        conn.execute(
                            "UPDATE bills SET sponsor_id = ? WHERE bill_id = ?",
                            [sponsor_id, bill_id]
                        )
                        sponsors_updated += 1

                # Extract short title from titles array
                titles = bill_data.get("titles", [])
                for t in titles:
                    if t.get("titleType", "").startswith("Short Title"):
                        short = t.get("title")
                        if short:
                            conn.execute(
                                "UPDATE bills SET short_title = ? WHERE bill_id = ?",
                                [short, bill_id]
                            )
                            break

                # Get cosponsors
                response = client.get_bill_cosponsors(congress, bill_type, bill_number)
                cosponsors = response.get("cosponsors", [])

                for cosponsor in cosponsors:
                    bioguide_id = cosponsor.get("bioguideId")
                    if not bioguide_id:
                        continue

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO bill_cosponsors (
                            bill_id, bioguide_id, cosponsor_date, is_original
                        ) VALUES (?, ?, ?, ?)
                        """,
                        [
                            bill_id,
                            bioguide_id,
                            cosponsor.get("sponsorshipDate"),
                            cosponsor.get("isOriginalCosponsor", False),
                        ]
                    )
                    inserted += 1

            except Exception as e:
                console.print(f"[dim]  {bill_id}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Updated {sponsors_updated} bill sponsors[/green]")
    console.print(f"[green]Inserted {inserted} cosponsors[/green]")


def sync_actions(congress: int = 118):
    """Sync actions for all bills in the database."""
    console.print(f"Syncing bill actions for Congress {congress}...")

    conn = duckdb.connect(str(DB_PATH))
    bills = conn.execute(
        "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
        [congress]
    ).fetchall()
    conn.close()

    if not bills:
        console.print("[yellow]No bills found. Run 'sync bills' first.[/yellow]")
        return

    console.print(f"Found {len(bills)} bills")

    conn = duckdb.connect(str(DB_PATH))
    inserted = 0

    with CongressClient() as client:
        for bill_id, bill_type, bill_number in track(bills, description="Fetching actions..."):
            try:
                response = client.get_bill_actions(congress, bill_type, bill_number)
                actions = response.get("actions", [])

                for idx, action in enumerate(actions):
                    action_code = action.get("actionCode", "")

                    if action_code.startswith("H"):
                        chamber = "house"
                    elif action_code.startswith("S"):
                        chamber = "senate"
                    else:
                        chamber = None

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO bill_actions (
                            bill_id, action_date, action_text, action_type, chamber, sequence
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            bill_id,
                            action.get("actionDate"),
                            action.get("text"),
                            action.get("type"),
                            chamber,
                            idx,
                        ]
                    )
                    inserted += 1

            except Exception as e:
                console.print(f"[dim]  {bill_id}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Inserted {inserted} actions[/green]")


def sync_subjects(congress: int = 118):
    """Sync legislative subject tags for all bills in the database."""
    console.print(f"Syncing bill subjects for Congress {congress}...")

    conn = duckdb.connect(str(DB_PATH))
    bills = conn.execute(
        "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
        [congress]
    ).fetchall()
    conn.close()

    if not bills:
        console.print("[yellow]No bills found. Run 'sync bills' first.[/yellow]")
        return

    console.print(f"Found {len(bills)} bills")

    conn = duckdb.connect(str(DB_PATH))
    inserted = 0

    with CongressClient() as client:
        for bill_id, bill_type, bill_number in track(bills, description="Fetching subjects..."):
            try:
                response = client.get_bill_subjects(congress, bill_type, bill_number)
                subjects = response.get("subjects", {})

                # Legislative subjects (many per bill)
                for subj in subjects.get("legislativeSubjects", []):
                    name = subj.get("name")
                    if name:
                        conn.execute(
                            "INSERT OR REPLACE INTO bill_subjects (bill_id, subject) VALUES (?, ?)",
                            [bill_id, name]
                        )
                        inserted += 1

                # Policy area (update if missing from initial sync)
                policy = subjects.get("policyArea", {})
                if policy and policy.get("name"):
                    conn.execute(
                        "UPDATE bills SET policy_area = ? WHERE bill_id = ? AND policy_area IS NULL",
                        [policy["name"], bill_id]
                    )

            except Exception as e:
                console.print(f"[dim]  {bill_id}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Inserted {inserted} subject tags[/green]")


def sync_summaries(congress: int = 118):
    """Sync CRS summaries and text version URLs for all bills."""
    console.print(f"Syncing bill summaries for Congress {congress}...")

    conn = duckdb.connect(str(DB_PATH))
    bills = conn.execute(
        "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
        [congress]
    ).fetchall()
    conn.close()

    if not bills:
        console.print("[yellow]No bills found. Run 'sync bills' first.[/yellow]")
        return

    console.print(f"Found {len(bills)} bills")

    conn = duckdb.connect(str(DB_PATH))
    summaries_updated = 0
    text_updated = 0

    with CongressClient() as client:
        for bill_id, bill_type, bill_number in track(bills, description="Fetching summaries..."):
            try:
                # Fetch summary
                sum_response = client.get_bill_summaries(congress, bill_type, bill_number)
                summaries = sum_response.get("summaries", [])
                if summaries:
                    # Use the most recent summary (last in list)
                    latest = summaries[-1]
                    text = latest.get("text", "")
                    if text:
                        clean = re.sub(r"<[^>]+>", "", text).strip()
                        conn.execute(
                            "UPDATE bills SET summary = ? WHERE bill_id = ?",
                            [clean, bill_id]
                        )
                        summaries_updated += 1

                # Fetch text versions
                text_response = client.get_bill_text(congress, bill_type, bill_number)
                versions = text_response.get("textVersions", [])
                if versions:
                    # Use the most recent text version
                    latest_text = versions[-1]
                    formats = latest_text.get("formats", [])
                    # Prefer PDF, fall back to HTML
                    url = None
                    for fmt in formats:
                        if fmt.get("type") == "Formatted Text (PDF)":
                            url = fmt.get("url")
                            break
                    if not url:
                        for fmt in formats:
                            if fmt.get("url"):
                                url = fmt.get("url")
                                break
                    if url:
                        conn.execute(
                            "UPDATE bills SET full_text_url = ? WHERE bill_id = ?",
                            [url, bill_id]
                        )
                        text_updated += 1

            except Exception as e:
                console.print(f"[dim]  {bill_id}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Updated {summaries_updated} summaries, {text_updated} text URLs[/green]")


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
