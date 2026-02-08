"""Sync votes from Congress.gov API to DuckDB."""

import duckdb
from pathlib import Path
from rich.console import Console
from rich.progress import track

from ingestion.client import CongressClient

console = Console()
DB_PATH = Path(__file__).parent.parent / "db" / "distillgov.duckdb"


def sync_votes(congress: int = 118):
    """Sync roll call votes from a Congress into DuckDB.

    Note: Congress.gov API currently only has House votes from 118th Congress (2023+).
    Senate votes may require a different data source.
    """
    console.print(f"Fetching votes from Congress {congress}...")

    with CongressClient() as client:
        votes = []
        offset = 0

        while True:
            try:
                response = client.get_votes(congress=congress, chamber="house", offset=offset)
                batch = response.get("houseVotes", response.get("votes", []))

                if not batch:
                    break

                votes.extend(batch)
                offset += len(batch)

                # Limit for initial sync
                if offset >= 500:
                    console.print("[dim]Limited to 500 votes[/dim]")
                    break

                if offset >= response.get("pagination", {}).get("count", 0):
                    break

            except Exception as e:
                console.print(f"[yellow]Vote API error: {e}[/yellow]")
                break

        console.print(f"Fetched {len(votes)} votes")

    if not votes:
        console.print("[yellow]No votes fetched. Vote endpoint may require different parameters.[/yellow]")
        return

    # Transform and load into DuckDB
    conn = duckdb.connect(str(DB_PATH))

    inserted = 0
    for vote in track(votes, description="Loading votes..."):
        roll_call = vote.get("rollCallNumber") or vote.get("rollCall")
        if not roll_call:
            continue

        vote_id = f"{congress}-house-{roll_call}"

        conn.execute(
            """
            INSERT OR REPLACE INTO votes (
                vote_id, congress, chamber, roll_call,
                vote_date, question, description, result,
                yea_count, nay_count, present_count, not_voting,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                vote_id,
                congress,
                "house",
                roll_call,
                vote.get("date") or vote.get("actionDate"),
                vote.get("question"),
                vote.get("description"),
                vote.get("result"),
                vote.get("totals", {}).get("yea"),
                vote.get("totals", {}).get("nay"),
                vote.get("totals", {}).get("present"),
                vote.get("totals", {}).get("notVoting"),
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} votes[/green]")


if __name__ == "__main__":
    sync_votes()
