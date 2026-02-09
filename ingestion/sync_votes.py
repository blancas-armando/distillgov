"""Sync votes from Congress.gov API and senate.gov XML to DuckDB."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import duckdb
from rich.console import Console
from rich.progress import track

from config import DB_PATH
from ingestion.client import CongressClient
from ingestion.constants import check_consecutive_errors
from ingestion.senate_client import SenateClient

console = Console()

# Legislation type abbreviations used in the Congress.gov API → bill_type codes
_LEG_TYPE_MAP: dict[str, str] = {
    "HR": "hr",
    "S": "s",
    "HJRES": "hjres",
    "SJRES": "sjres",
    "HCONRES": "hconres",
    "SCONRES": "sconres",
    "HRES": "hres",
    "SRES": "sres",
    "H.R.": "hr",
    "S.": "s",
}

# Senate <issue> patterns → (bill_type, number)
_SENATE_ISSUE_RE = re.compile(
    r"^(?:"
    r"H\.R\.\s*(\d+)"         # H.R. 1234
    r"|S\.\s*(\d+)"           # S. 567
    r"|H\.J\.Res\.\s*(\d+)"   # H.J.Res. 12
    r"|S\.J\.Res\.\s*(\d+)"   # S.J.Res. 34
    r"|H\.Con\.Res\.\s*(\d+)" # H.Con.Res. 56
    r"|S\.Con\.Res\.\s*(\d+)" # S.Con.Res. 78
    r"|H\.Res\.\s*(\d+)"      # H.Res. 90
    r"|S\.Res\.\s*(\d+)"      # S.Res. 12
    r")$"
)

_SENATE_ISSUE_TYPES = [
    "hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"
]

# Legislators CSV for lis_id → bioguide_id lookup
_LEGISLATORS_PATH = Path(__file__).parent.parent / "db" / "legislators.csv"


def _build_house_bill_id(congress: int, leg_type: str, leg_num: str) -> str | None:
    """Build a bill_id from House vote legislation metadata."""
    if not leg_type or not leg_num:
        return None
    bill_type = _LEG_TYPE_MAP.get(leg_type.strip())
    if not bill_type:
        return None
    try:
        num = int(leg_num)
    except ValueError:
        return None
    return f"{congress}-{bill_type}-{num}"


def _parse_senate_issue(congress: int, issue: str) -> str | None:
    """Parse a Senate vote <issue> field into a bill_id.

    Examples:
        "H.R. 1234" → "118-hr-1234"
        "S. 567"     → "118-s-567"
        "PN36"       → None (nomination)
    """
    if not issue:
        return None
    m = _SENATE_ISSUE_RE.match(issue.strip())
    if not m:
        return None
    for bill_type, group_val in zip(_SENATE_ISSUE_TYPES, m.groups()):
        if group_val:
            return f"{congress}-{bill_type}-{group_val}"
    return None


def _load_lis_to_bioguide() -> dict[str, str]:
    """Load lis_id → bioguide_id mapping from legislators.csv."""
    mapping: dict[str, str] = {}
    if not _LEGISLATORS_PATH.exists():
        console.print(f"[yellow]legislators.csv not found at {_LEGISLATORS_PATH}[/yellow]")
        return mapping
    with open(_LEGISLATORS_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lis_id = row.get("lis_id", "").strip()
            bioguide_id = row.get("bioguide_id", "").strip()
            if lis_id and bioguide_id:
                mapping[lis_id] = bioguide_id
    return mapping


# ---------------------------------------------------------------------------
# House votes (Congress.gov API)
# ---------------------------------------------------------------------------


def sync_votes(congress: int = 118, with_members: bool = False, limit: int = 500):
    """Sync House roll call votes from Congress.gov into DuckDB.

    Args:
        congress: Congress number (e.g., 118)
        with_members: If True, also fetch individual member voting positions
        limit: Max votes to fetch (0 for all)
    """
    console.print(f"Fetching House votes from Congress {congress}...")

    with CongressClient() as client:
        votes: list[dict] = []
        offset = 0

        while True:
            try:
                response = client.get_votes(
                    congress=congress,
                    chamber="house",
                    offset=offset,
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

    conn = duckdb.connect(str(DB_PATH))

    inserted = 0
    for vote in track(votes, description="Loading votes..."):
        roll_call = vote.get("rollCallNumber")
        session = vote.get("sessionNumber", 1)

        if not roll_call:
            continue

        vote_id = f"{congress}-house-{session}-{roll_call}"

        start_date = vote.get("startDate", "")
        vote_date = start_date.split("T")[0] if start_date else None

        leg_type = vote.get("legislationType", "")
        leg_num = vote.get("legislationNumber", "")
        amendment_author = vote.get("amendmentAuthor", "")

        if amendment_author:
            question = amendment_author
        elif leg_type and leg_num:
            question = f"{leg_type} {leg_num}"
        else:
            question = vote.get("voteType", "")

        bill_id = _build_house_bill_id(congress, leg_type, str(leg_num)) if leg_num else None

        # Extract vote counts if present in API response
        yea_count = vote.get("yeaCount") or vote.get("yeas")
        nay_count = vote.get("nayCount") or vote.get("nays")
        present_count = vote.get("presentCount")
        not_voting = vote.get("notVotingCount")

        conn.execute(
            """
            INSERT OR REPLACE INTO votes (
                vote_id, congress, chamber, session, roll_call,
                vote_date, question, description, result,
                bill_id, yea_count, nay_count, present_count, not_voting,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                bill_id,
                yea_count,
                nay_count,
                present_count,
                not_voting,
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} votes[/green]")

    if with_members:
        sync_member_votes(congress, votes)


def sync_member_votes(congress: int, votes: list[dict] | None = None, limit: int = 100):
    """Sync individual House member voting positions.

    Args:
        congress: Congress number
        votes: List of vote records (if None, fetches from database)
        limit: Max votes to fetch member positions for (0 for all)
    """
    conn = duckdb.connect(str(DB_PATH))

    if votes is None:
        query = "SELECT vote_id, session, roll_call FROM votes WHERE congress = ? AND chamber = 'house'"
        if limit > 0:
            query += f" LIMIT {limit}"
        db_votes = conn.execute(query, [congress]).fetchall()
        votes = [{"_vote_id": v[0], "sessionNumber": v[1], "rollCallNumber": v[2]} for v in db_votes]

    if not votes:
        console.print("[yellow]No votes found. Run 'sync votes' first.[/yellow]")
        conn.close()
        return

    if limit > 0 and len(votes) > limit:
        votes = votes[:limit]

    console.print(f"\n[blue]Fetching House member positions for {len(votes)} votes...[/blue]")

    inserted = 0
    consecutive_errors = 0
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
                        [vote_id, bioguide_id, position],
                    )
                    inserted += 1

                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                console.print(f"[dim]  Vote {roll_call}: {e}[/dim]")
                check_consecutive_errors(consecutive_errors, e)
                continue

    conn.close()
    console.print(f"[green]Inserted {inserted} House member votes[/green]")


# ---------------------------------------------------------------------------
# Senate votes (senate.gov XML)
# ---------------------------------------------------------------------------


def sync_senate_votes(congress: int = 118, session: int = 1):
    """Sync Senate roll call votes from senate.gov XML into DuckDB.

    Args:
        congress: Congress number (e.g., 118)
        session: Session number (1 or 2)
    """
    console.print(f"Fetching Senate votes for Congress {congress}, session {session}...")

    with SenateClient() as client:
        menu = client.get_vote_menu(congress, session)

    if menu is None:
        console.print("[yellow]No Senate vote menu found.[/yellow]")
        return

    vote_elements = menu.findall(".//vote")
    console.print(f"Total: {len(vote_elements)} Senate votes in menu")

    if not vote_elements:
        return

    conn = duckdb.connect(str(DB_PATH))

    _month_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }

    inserted = 0
    for vote_el in track(vote_elements, description="Loading Senate votes..."):
        vote_number = vote_el.findtext("vote_number", "").strip()
        if not vote_number:
            continue

        vote_id = f"{congress}-senate-{session}-{vote_number}"

        # Parse date: "19-Dec" → needs year from session context
        vote_date_raw = vote_el.findtext("vote_date", "").strip()
        vote_date = None
        if vote_date_raw:
            parts = vote_date_raw.split("-")
            if len(parts) == 2:
                day = parts[0].zfill(2)
                month = _month_map.get(parts[1])
                if month:
                    # Session 1 starts in odd year, session 2 in even year
                    year = 2023 + (congress - 118) * 2 + (session - 1)
                    vote_date = f"{year}-{month}-{day}"

        issue = vote_el.findtext("issue", "").strip()
        question = vote_el.findtext("question", "").strip()
        result = vote_el.findtext("result", "").strip()
        title = vote_el.findtext("title", "").strip()

        tally = vote_el.find("vote_tally")
        yea_count = None
        nay_count = None
        if tally is not None:
            yea_text = tally.findtext("yeas", "").strip()
            nay_text = tally.findtext("nays", "").strip()
            yea_count = int(yea_text) if yea_text.isdigit() else None
            nay_count = int(nay_text) if nay_text.isdigit() else None

        bill_id = _parse_senate_issue(congress, issue)

        description = title or issue or None

        conn.execute(
            """
            INSERT OR REPLACE INTO votes (
                vote_id, congress, chamber, session, roll_call,
                vote_date, question, description, result,
                bill_id, yea_count, nay_count,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                vote_id,
                congress,
                "senate",
                session,
                int(vote_number),
                vote_date,
                question,
                description,
                result,
                bill_id,
                yea_count,
                nay_count,
            ],
        )
        inserted += 1

    conn.close()
    console.print(f"[green]Inserted {inserted} Senate votes[/green]")


def sync_senate_member_votes(congress: int = 118, session: int = 1):
    """Sync individual Senate member voting positions from senate.gov XML.

    Fetches detail XML for each vote to get per-member positions.
    Uses legislators.csv to map lis_member_id → bioguide_id.

    Args:
        congress: Congress number (e.g., 118)
        session: Session number (1 or 2)
    """
    lis_to_bioguide = _load_lis_to_bioguide()
    if not lis_to_bioguide:
        console.print("[red]Cannot sync Senate member votes without legislators.csv[/red]")
        return

    console.print(f"Loaded {len(lis_to_bioguide)} lis_id → bioguide_id mappings")

    conn = duckdb.connect(str(DB_PATH))

    # Get Senate votes from database
    db_votes = conn.execute(
        "SELECT vote_id, roll_call FROM votes WHERE congress = ? AND chamber = 'senate' AND session = ?",
        [congress, session],
    ).fetchall()

    if not db_votes:
        console.print("[yellow]No Senate votes found. Run 'sync senate-votes' first.[/yellow]")
        conn.close()
        return

    console.print(f"\n[blue]Fetching Senate member positions for {len(db_votes)} votes...[/blue]")

    inserted = 0
    unmatched_lis: set[str] = set()

    with SenateClient() as client:
        for vote_id, roll_call in track(db_votes, description="Fetching Senate member votes..."):
            detail = client.get_vote_detail(congress, session, roll_call)
            if detail is None:
                continue

            members = detail.findall(".//member")
            for member_el in members:
                lis_id = member_el.findtext("lis_member_id", "").strip()
                vote_cast = member_el.findtext("vote_cast", "").strip()

                if not lis_id or not vote_cast:
                    continue

                bioguide_id = lis_to_bioguide.get(lis_id)
                if not bioguide_id:
                    unmatched_lis.add(lis_id)
                    continue

                # Normalize Senate positions to match House conventions
                position = {
                    "Yea": "Yes",
                    "Nay": "No",
                    "Not Voting": "Not Voting",
                    "Present": "Present",
                }.get(vote_cast, vote_cast)

                conn.execute(
                    """
                    INSERT OR REPLACE INTO member_votes (
                        vote_id, bioguide_id, position
                    ) VALUES (?, ?, ?)
                    """,
                    [vote_id, bioguide_id, position],
                )
                inserted += 1

    conn.close()

    if unmatched_lis:
        console.print(f"[dim]  {len(unmatched_lis)} unmatched lis_ids (missing from legislators.csv)[/dim]")

    console.print(f"[green]Inserted {inserted} Senate member votes[/green]")


if __name__ == "__main__":
    sync_votes()
