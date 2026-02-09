"""Sync votes from Congress.gov API and senate.gov XML to DuckDB."""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from rich.progress import track

from ingestion.client import CongressClient
from ingestion.constants import check_consecutive_errors
from ingestion.db import get_conn
from ingestion.senate_client import SenateClient
from ingestion.sync_meta import get_last_sync, set_last_sync

log = logging.getLogger(__name__)

# Legislation type abbreviations used in the Congress.gov API → bill_type codes
_LEG_TYPE_MAP: dict[str, str] = {
    "HR": "hr", "S": "s", "HJRES": "hjres", "SJRES": "sjres",
    "HCONRES": "hconres", "SCONRES": "sconres", "HRES": "hres", "SRES": "sres",
    "H.R.": "hr", "S.": "s",
}

# Senate <issue> patterns → (bill_type, number)
_SENATE_ISSUE_RE = re.compile(
    r"^(?:"
    r"H\.R\.\s*(\d+)"
    r"|S\.\s*(\d+)"
    r"|H\.J\.Res\.\s*(\d+)"
    r"|S\.J\.Res\.\s*(\d+)"
    r"|H\.Con\.Res\.\s*(\d+)"
    r"|S\.Con\.Res\.\s*(\d+)"
    r"|H\.Res\.\s*(\d+)"
    r"|S\.Res\.\s*(\d+)"
    r")$"
)

_SENATE_ISSUE_TYPES = [
    "hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"
]

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
    """Parse a Senate vote <issue> field into a bill_id."""
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
        log.warning("legislators.csv not found at %s", _LEGISLATORS_PATH)
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


def sync_votes(
    congress: int = 118,
    with_members: bool = False,
    limit: int = 500,
    full: bool = False,
):
    """Sync House roll call votes from Congress.gov into DuckDB.

    Incremental by default — only fetches votes updated since the last sync.
    """
    from_dt = None if full else get_last_sync(f"votes-{congress}")
    mode = "incremental" if from_dt else "full"
    log.info("Fetching House votes from Congress %d (%s)", congress, mode)
    if from_dt:
        log.info("  Since: %s", from_dt)

    with CongressClient() as client:
        votes: list[dict] = []
        offset = 0

        while True:
            try:
                response = client.get_votes(
                    congress=congress,
                    chamber="house",
                    offset=offset,
                    from_datetime=from_dt,
                )
                batch = response.get("houseRollCallVotes", [])

                if not batch:
                    break

                votes.extend(batch)
                offset += len(batch)
                log.info("  Fetched %d votes", len(votes))

                if limit > 0 and offset >= limit:
                    log.info("  Limited to %d votes", limit)
                    break

                if offset >= response.get("pagination", {}).get("count", 0):
                    break

            except Exception as e:
                log.warning("Vote API error: %s", e)
                break

        log.info("Total: %d votes", len(votes))

    if not votes:
        log.warning("No votes fetched")
        return

    with get_conn() as conn:
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
                    vote_id, congress, "house", session, roll_call,
                    vote_date, question, vote.get("voteType"),
                    vote.get("result"), bill_id, yea_count, nay_count,
                    present_count, not_voting,
                ],
            )
            inserted += 1

    log.info("Inserted %d votes", inserted)
    set_last_sync(f"votes-{congress}", inserted)

    if with_members:
        sync_member_votes(congress, votes)


def sync_member_votes(congress: int, votes: list[dict] | None = None, limit: int = 100):
    """Sync individual House member voting positions."""
    with get_conn() as conn:
        if votes is None:
            query = "SELECT vote_id, session, roll_call FROM votes WHERE congress = ? AND chamber = 'house'"
            if limit > 0:
                query += f" LIMIT {limit}"
            db_votes = conn.execute(query, [congress]).fetchall()
            votes = [{"_vote_id": v[0], "sessionNumber": v[1], "rollCallNumber": v[2]} for v in db_votes]

        if not votes:
            log.warning("No votes found. Run 'sync votes' first.")
            return

        if limit > 0 and len(votes) > limit:
            votes = votes[:limit]

        log.info("Fetching House member positions for %d votes", len(votes))

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
                    log.debug("  Vote %s: %s", roll_call, e)
                    check_consecutive_errors(consecutive_errors, e)
                    continue

    log.info("Inserted %d House member votes", inserted)


# ---------------------------------------------------------------------------
# Senate votes (senate.gov XML)
# ---------------------------------------------------------------------------


def sync_senate_votes(congress: int = 118, session: int = 1):
    """Sync Senate roll call votes from senate.gov XML into DuckDB."""
    log.info("Fetching Senate votes for Congress %d, session %d", congress, session)

    with SenateClient() as client:
        menu = client.get_vote_menu(congress, session)

    if menu is None:
        log.warning("No Senate vote menu found")
        return

    vote_elements = menu.findall(".//vote")
    log.info("Total: %d Senate votes in menu", len(vote_elements))

    if not vote_elements:
        return

    _month_map = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
    }

    with get_conn() as conn:
        inserted = 0
        for vote_el in track(vote_elements, description="Loading Senate votes..."):
            vote_number = vote_el.findtext("vote_number", "").strip()
            if not vote_number:
                continue

            vote_id = f"{congress}-senate-{session}-{vote_number}"

            vote_date_raw = vote_el.findtext("vote_date", "").strip()
            vote_date = None
            if vote_date_raw:
                parts = vote_date_raw.split("-")
                if len(parts) == 2:
                    day = parts[0].zfill(2)
                    month = _month_map.get(parts[1])
                    if month:
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
                    vote_id, congress, "senate", session, int(vote_number),
                    vote_date, question, description, result,
                    bill_id, yea_count, nay_count,
                ],
            )
            inserted += 1

    log.info("Inserted %d Senate votes", inserted)


def sync_senate_member_votes(congress: int = 118, session: int = 1):
    """Sync individual Senate member voting positions from senate.gov XML."""
    lis_to_bioguide = _load_lis_to_bioguide()
    if not lis_to_bioguide:
        log.error("Cannot sync Senate member votes without legislators.csv")
        return

    log.info("Loaded %d lis_id → bioguide_id mappings", len(lis_to_bioguide))

    with get_conn() as conn:
        db_votes = conn.execute(
            "SELECT vote_id, roll_call FROM votes WHERE congress = ? AND chamber = 'senate' AND session = ?",
            [congress, session],
        ).fetchall()

        if not db_votes:
            log.warning("No Senate votes found. Run 'sync senate-votes' first.")
            return

        log.info("Fetching Senate member positions for %d votes", len(db_votes))

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

                    position = {
                        "Yea": "Yes", "Nay": "No",
                        "Not Voting": "Not Voting", "Present": "Present",
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

    if unmatched_lis:
        log.debug("  %d unmatched lis_ids (missing from legislators.csv)", len(unmatched_lis))

    log.info("Inserted %d Senate member votes", inserted)


if __name__ == "__main__":
    sync_votes()
