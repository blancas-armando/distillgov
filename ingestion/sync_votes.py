"""Sync votes from Congress.gov API to DuckDB."""

from __future__ import annotations

import duckdb
from rich.console import Console
from rich.progress import track

from config import DB_PATH
from ingestion.client import CongressClient

console = Console()


def sync_votes(congress: int = 118, with_members: bool = False, limit: int = 500):
    """Sync roll call votes from a Congress into DuckDB.

    Args:
        congress: Congress number (e.g., 118)
        with_members: If True, also fetch individual member voting positions
        limit: Max votes to fetch (0 for all)

    Note: Congress.gov API currently only has House votes.
    Senate votes may require a different data source.
    """
    console.print(f"Fetching House votes from Congress {congress}...")

    with CongressClient() as client:
        votes = []
        offset = 0

        while True:
            try:
                response = client.get_votes(
                    congress=congress,
                    chamber="house",
                    offset=offset
                )
                batch = response.get("houseRollCallVotes", [])

                if not batch:
                    break

                votes.extend(batch)
                offset += len(batch)
                console.print(f"  Fetched {len(votes)} votes...")

                if limit > 0 and offset >= limit:
                    console.print(f"  [dim]Limited to {limit} votes[/dim]")
                    break

                if offset >= response.get("pagination", {}).get("count", 0):
                    break

            except Exception as e:
                console.print(f"[yellow]Vote API error: {e}[/yellow]")
                break

        console.print(f"Total: {len(votes)} votes")

    if not votes:
        console.print("[yellow]No votes fetched.[/yellow]")
        return

    # Transform and load into DuckDB
    conn = duckdb.connect(str(DB_PATH))

    inserted = 0
    for vote in track(votes, description="Loading votes..."):
        roll_call = vote.get("rollCallNumber")
        session = vote.get("sessionNumber", 1)

        if not roll_call:
            continue

        vote_id = f"{congress}-house-{session}-{roll_call}"

        # Parse date from startDate
        start_date = vote.get("startDate", "")
        vote_date = start_date.split("T")[0] if start_date else None

        # Build question from legislation info
        leg_type = vote.get("legislationType", "")
        leg_num = vote.get("legislationNumber", "")
        amendment_author = vote.get("amendmentAuthor", "")

        if amendment_author:
            question = f"{amendment_author}"
        elif leg_type and leg_num:
            question = f"{leg_type} {leg_num}"
        else:
            question = vote.get("voteType", "")

        conn.execute(
            """
            INSERT OR REPLACE INTO votes (
                vote_id, congress, chamber, session, roll_call,
                vote_date, question, description, result,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                vote_id,
                congress,
                "house",
                session,
                roll_call,
                vote_date,
                question,
                vote.get("voteType"),
                vote.get("result"),
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} votes[/green]")

    if with_members:
        sync_member_votes(congress, votes)


def sync_member_votes(congress: int, votes: list[dict] | None = None, limit: int = 100):
    """Sync individual member voting positions.

    Args:
        congress: Congress number
        votes: List of vote records (if None, fetches from database)
        limit: Max votes to fetch member positions for (0 for all)
    """
    conn = duckdb.connect(str(DB_PATH))

    if votes is None:
        # Get votes from database
        query = "SELECT vote_id, session, roll_call FROM votes WHERE congress = ? AND chamber = 'house'"
        if limit > 0:
            query += f" LIMIT {limit}"
        db_votes = conn.execute(query, [congress]).fetchall()
        votes = [{"_vote_id": v[0], "sessionNumber": v[1], "rollCallNumber": v[2]} for v in db_votes]

    if not votes:
        console.print("[yellow]No votes found. Run 'sync votes' first.[/yellow]")
        conn.close()
        return

    # Apply limit if we have more votes than the limit
    if limit > 0 and len(votes) > limit:
        votes = votes[:limit]

    console.print(f"\n[blue]Fetching member positions for {len(votes)} votes...[/blue]")

    inserted = 0
    with CongressClient() as client:
        for vote in track(votes, description="Fetching member votes..."):
            roll_call = vote.get("rollCallNumber")
            session = vote.get("sessionNumber", 1)

            if not roll_call:
                continue

            vote_id = vote.get("_vote_id") or f"{congress}-house-{session}-{roll_call}"

            try:
                response = client.get_vote_members(congress, session, roll_call)
                vote_data = response.get("houseRollCallVoteMemberVotes", {})
                members = vote_data.get("results", [])

                for member in members:
                    bioguide_id = member.get("bioguideID")
                    position = member.get("voteCast")

                    if not bioguide_id or not position:
                        continue

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO member_votes (
                            vote_id, bioguide_id, position
                        ) VALUES (?, ?, ?)
                        """,
                        [vote_id, bioguide_id, position]
                    )
                    inserted += 1

            except Exception as e:
                console.print(f"[dim]  Vote {roll_call}: {e}[/dim]")
                continue

    conn.close()
    console.print(f"[green]Inserted {inserted} member votes[/green]")


if __name__ == "__main__":
    sync_votes()
