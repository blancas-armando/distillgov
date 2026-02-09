"""Members API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import escape_like, get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Member(BaseModel):
    bioguide_id: str
    first_name: str | None
    last_name: str | None
    full_name: str | None
    party: str | None
    state: str | None
    district: int | None
    chamber: str | None
    is_current: bool | None
    image_url: str | None
    official_url: str | None


class MemberCommittee(BaseModel):
    committee_id: str
    name: str
    role: str | None


class RecentVote(BaseModel):
    vote_id: str
    vote_date: date | None
    question: str | None
    position: str


class RecentBill(BaseModel):
    bill_id: str
    title: str | None
    introduced_date: date | None
    status: str | None


class MemberDetail(Member):
    phone: str | None = None
    office_address: str | None = None
    contact_form: str | None = None
    twitter: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    leadership_role: str | None = None
    start_date: date | None = None
    committees: list[MemberCommittee] = []
    recent_votes: list[RecentVote] = []
    recent_bills: list[RecentBill] = []
    bills_sponsored: int = 0
    bills_enacted: int = 0
    bills_passed: int = 0
    sponsor_success_rate: float = 0
    votes_cast: int = 0
    votes_missed: int = 0
    attendance_rate: float | None = None
    party_loyalty_pct: float | None = None
    activity_score: float | None = None


class MemberComparison(BaseModel):
    members: list[MemberDetail]
    shared_votes: int
    agreement_rate: float | None
    shared_bills_cosponsored: int


class MemberList(BaseModel):
    members: list[Member]
    total: int
    offset: int
    limit: int


class MemberVote(BaseModel):
    vote_id: str
    vote_date: date | None
    chamber: str | None
    question: str | None
    description: str | None
    result: str | None
    bill_id: str | None
    position: str


class MemberVoteList(BaseModel):
    votes: list[MemberVote]
    total: int
    offset: int
    limit: int


class MemberBill(BaseModel):
    bill_id: str
    bill_type: str
    bill_number: int
    title: str | None
    introduced_date: date | None
    status: str | None
    policy_area: str | None
    role: str  # "sponsor" or "cosponsor"


class MemberBillList(BaseModel):
    bills: list[MemberBill]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/by-zip/{zip_code}", response_model=MemberList)
def get_members_by_zip(zip_code: str):
    """Find representatives and senators for a zip code.

    Returns House representatives for the matching district(s) plus
    both senators for the state. A zip code can span multiple districts,
    so multiple House reps may be returned.
    """
    if len(zip_code) != 5 or not zip_code.isdigit():
        raise HTTPException(status_code=400, detail="Zip code must be 5 digits")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT m.bioguide_id, m.first_name, m.last_name, m.full_name,
                   m.party, m.state, m.district, m.chamber, m.is_current,
                   m.image_url, m.official_url
            FROM zip_districts z
            JOIN members m ON z.state = m.state AND z.district = m.district AND m.chamber = 'house'
            WHERE z.zcta = ? AND m.is_current = TRUE
            UNION ALL
            SELECT m.bioguide_id, m.first_name, m.last_name, m.full_name,
                   m.party, m.state, m.district, m.chamber, m.is_current,
                   m.image_url, m.official_url
            FROM members m
            WHERE m.state = (SELECT z.state FROM zip_districts z WHERE z.zcta = ? LIMIT 1)
              AND m.chamber = 'senate' AND m.is_current = TRUE
            """,
            [zip_code, zip_code],
        ).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No representatives found for this zip code")

        members = [_row_to_member(r) for r in rows]
        return MemberList(members=members, total=len(members), offset=0, limit=len(members))


@router.get("", response_model=MemberList)
def list_members(
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    party: str | None = Query(None, description="Filter by party: D, R, I"),
    state: str | None = Query(None, description="Filter by state code: CA, NY, TX..."),
    current: bool = Query(True, description="Only show current members"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """List all members of Congress."""
    with get_db() as conn:
        conditions: list[str] = []
        params: list[object] = []

        if current:
            conditions.append("is_current = TRUE")
        if chamber:
            conditions.append("chamber = ?")
            params.append(chamber.lower())
        if party:
            conditions.append("party = ?")
            params.append(party.upper())
        if state:
            conditions.append("state = ?")
            params.append(state.upper())

        where = " AND ".join(conditions) if conditions else "1=1"

        total = conn.execute(
            f"SELECT COUNT(*) FROM members WHERE {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT bioguide_id, first_name, last_name, full_name,
                   party, state, district, chamber, is_current,
                   image_url, official_url
            FROM members
            WHERE {where}
            ORDER BY state, last_name
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        members = [_row_to_member(r) for r in rows]
        return MemberList(members=members, total=total, offset=offset, limit=limit)


@router.get("/compare", response_model=MemberComparison)
def compare_members(
    ids: str = Query(..., description="Comma-separated bioguide IDs (e.g., A000001,B000002)"),
):
    """Compare two members side-by-side.

    Returns stats for both members plus their voting agreement rate
    and number of bills they've both cosponsored.
    """
    id_list = [x.strip() for x in ids.split(",") if x.strip()]
    if len(id_list) != 2:
        raise HTTPException(status_code=400, detail="Provide exactly 2 bioguide IDs separated by a comma")

    with get_db() as conn:
        members = []
        for bid in id_list:
            detail = _build_member_detail(conn, bid)
            if not detail:
                raise HTTPException(status_code=404, detail=f"Member {bid} not found")
            members.append(detail)

        # Voting agreement: votes where both participated
        agreement = conn.execute(
            """
            SELECT
                count(*) as shared,
                count(*) filter (where a.position = b.position) as agreed
            FROM member_votes a
            JOIN member_votes b ON a.vote_id = b.vote_id
            WHERE a.bioguide_id = ? AND b.bioguide_id = ?
              AND a.position NOT IN ('Not Voting', 'Present')
              AND b.position NOT IN ('Not Voting', 'Present')
            """,
            id_list,
        ).fetchone()

        shared_votes = agreement[0] if agreement else 0
        agreed = agreement[1] if agreement else 0
        agreement_rate = round(100.0 * agreed / shared_votes, 1) if shared_votes > 0 else None

        # Bills both cosponsored
        shared_bills = conn.execute(
            """
            SELECT count(*) FROM bill_cosponsors a
            JOIN bill_cosponsors b ON a.bill_id = b.bill_id
            WHERE a.bioguide_id = ? AND b.bioguide_id = ?
            """,
            id_list,
        ).fetchone()[0]

        return MemberComparison(
            members=members,
            shared_votes=shared_votes,
            agreement_rate=agreement_rate,
            shared_bills_cosponsored=shared_bills,
        )


@router.get("/{bioguide_id}", response_model=MemberDetail)
def get_member(bioguide_id: str):
    """Get a single member with enriched stats.

    Includes contact info, social media, committee assignments,
    sponsorship metrics, voting attendance, and party loyalty.
    """
    with get_db() as conn:
        detail = _build_member_detail(conn, bioguide_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Member not found")
        return detail


@router.get("/{bioguide_id}/votes", response_model=MemberVoteList)
def get_member_votes(
    bioguide_id: str,
    subject: str | None = Query(None, description="Filter by legislative subject (e.g., Healthcare, Taxation)"),
    policy_area: str | None = Query(None, description="Filter by policy area"),
    passage_only: bool = Query(False, description="Only show passage/final votes (exclude procedural)"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """Get a member's voting record.

    Filter by `subject` to answer "how did my rep vote on healthcare?"
    Use `passage_only=true` to skip procedural votes and see substantive ones.
    """
    with get_db() as conn:
        _assert_member_exists(conn, bioguide_id)

        conditions = ["mv.bioguide_id = ?"]
        params: list[object] = [bioguide_id]

        joins = "JOIN votes v ON mv.vote_id = v.vote_id"

        if subject:
            joins += " JOIN bills b ON v.bill_id = b.bill_id JOIN bill_subjects bs ON b.bill_id = bs.bill_id"
            conditions.append("bs.subject ILIKE ? ESCAPE '\\'")
            params.append(f"%{escape_like(subject)}%")

        if policy_area:
            if "bills b" not in joins:
                joins += " JOIN bills b ON v.bill_id = b.bill_id"
            conditions.append("b.policy_area = ?")
            params.append(policy_area)

        if passage_only:
            conditions.append(
                "(v.question ILIKE '%passage%' OR v.question ILIKE '%pass%' "
                "OR v.question ILIKE '%conference report%' OR v.question ILIKE '%override%')"
            )

        where = " AND ".join(conditions)

        total = conn.execute(
            f"SELECT COUNT(*) FROM member_votes mv {joins} WHERE {where}",
            params,
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT v.vote_id, v.vote_date, v.chamber, v.question,
                   v.description, v.result, v.bill_id, mv.position
            FROM member_votes mv
            {joins}
            WHERE {where}
            ORDER BY v.vote_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        votes = [
            MemberVote(
                vote_id=r[0], vote_date=r[1], chamber=r[2], question=r[3],
                description=r[4], result=r[5], bill_id=r[6], position=r[7],
            )
            for r in rows
        ]
        return MemberVoteList(votes=votes, total=total, offset=offset, limit=limit)


@router.get("/{bioguide_id}/bills", response_model=MemberBillList)
def get_member_bills(
    bioguide_id: str,
    role: str | None = Query(None, description="Filter by role: sponsor, cosponsor"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """Get bills a member has sponsored or cosponsored."""
    with get_db() as conn:
        _assert_member_exists(conn, bioguide_id)

        # Sponsored bills
        sponsored_cte = """
            SELECT bill_id, bill_type, bill_number, title, introduced_date,
                   status, policy_area, 'sponsor' as role
            FROM bills WHERE sponsor_id = ?
        """

        # Cosponsored bills
        cosponsored_cte = """
            SELECT b.bill_id, b.bill_type, b.bill_number, b.title, b.introduced_date,
                   b.status, b.policy_area, 'cosponsor' as role
            FROM bill_cosponsors c
            JOIN bills b ON c.bill_id = b.bill_id
            WHERE c.bioguide_id = ?
        """

        if role == "sponsor":
            query = sponsored_cte
            count_query = "SELECT COUNT(*) FROM bills WHERE sponsor_id = ?"
            params: list[object] = [bioguide_id]
        elif role == "cosponsor":
            query = cosponsored_cte
            count_query = "SELECT COUNT(*) FROM bill_cosponsors WHERE bioguide_id = ?"
            params = [bioguide_id]
        else:
            query = f"{sponsored_cte} UNION ALL {cosponsored_cte}"
            count_query = f"""
                SELECT (SELECT COUNT(*) FROM bills WHERE sponsor_id = ?)
                     + (SELECT COUNT(*) FROM bill_cosponsors WHERE bioguide_id = ?)
            """
            params = [bioguide_id, bioguide_id]

        total = conn.execute(count_query, params).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT * FROM ({query})
            ORDER BY introduced_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        bills = [
            MemberBill(
                bill_id=r[0], bill_type=r[1], bill_number=r[2], title=r[3],
                introduced_date=r[4], status=r[5], policy_area=r[6], role=r[7],
            )
            for r in rows
        ]
        return MemberBillList(bills=bills, total=total, offset=offset, limit=limit)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_member(r: tuple) -> Member:
    return Member(
        bioguide_id=r[0], first_name=r[1], last_name=r[2], full_name=r[3],
        party=r[4], state=r[5], district=r[6], chamber=r[7], is_current=r[8],
        image_url=r[9], official_url=r[10],
    )


def _get_committees(conn, bioguide_id: str) -> list[MemberCommittee]:
    """Get committee assignments for a member."""
    try:
        rows = conn.execute(
            """
            SELECT cm.committee_id, c.name, cm.role
            FROM committee_members cm
            JOIN committees c ON cm.committee_id = c.committee_id
            WHERE cm.bioguide_id = ?
            ORDER BY c.name
            """,
            [bioguide_id],
        ).fetchall()
        return [MemberCommittee(committee_id=r[0], name=r[1], role=r[2]) for r in rows]
    except Exception:
        return []


def _get_contact_fields(conn, bioguide_id: str) -> dict:
    """Get contact and social media fields for a member."""
    try:
        row = conn.execute(
            """
            SELECT phone, office_address, contact_form, twitter, facebook, youtube
            FROM members WHERE bioguide_id = ?
            """,
            [bioguide_id],
        ).fetchone()
        if row:
            return {
                "phone": row[0], "office_address": row[1], "contact_form": row[2],
                "twitter": row[3], "facebook": row[4], "youtube": row[5],
            }
    except Exception:
        pass
    return {}


def _get_recent_votes(conn, bioguide_id: str, limit: int = 5) -> list[RecentVote]:
    """Get a member's most recent votes."""
    try:
        rows = conn.execute(
            """
            SELECT v.vote_id, v.vote_date, v.question, mv.position
            FROM member_votes mv
            JOIN votes v ON mv.vote_id = v.vote_id
            WHERE mv.bioguide_id = ?
            ORDER BY v.vote_date DESC NULLS LAST
            LIMIT ?
            """,
            [bioguide_id, limit],
        ).fetchall()
        return [
            RecentVote(vote_id=r[0], vote_date=r[1], question=r[2], position=r[3])
            for r in rows
        ]
    except Exception:
        return []


def _get_recent_bills(conn, bioguide_id: str, limit: int = 5) -> list[RecentBill]:
    """Get a member's most recently sponsored bills."""
    try:
        rows = conn.execute(
            """
            SELECT bill_id, title, introduced_date, status
            FROM bills
            WHERE sponsor_id = ?
            ORDER BY introduced_date DESC NULLS LAST
            LIMIT ?
            """,
            [bioguide_id, limit],
        ).fetchall()
        return [
            RecentBill(bill_id=r[0], title=r[1], introduced_date=r[2], status=r[3])
            for r in rows
        ]
    except Exception:
        return []


def _build_member_detail(conn, bioguide_id: str) -> MemberDetail | None:
    """Build a full MemberDetail with stats, contact info, committees, and recent activity."""
    contact = _get_contact_fields(conn, bioguide_id)
    committees = _get_committees(conn, bioguide_id)
    recent_votes = _get_recent_votes(conn, bioguide_id)
    recent_bills = _get_recent_bills(conn, bioguide_id)

    # Try fct_members first (has computed stats)
    try:
        row = conn.execute(
            """
            SELECT bioguide_id, first_name, last_name, full_name,
                   party, state, district, chamber, is_current,
                   image_url, official_url, leadership_role, start_date,
                   bills_sponsored, bills_enacted, bills_passed, sponsor_success_rate,
                   votes_cast, votes_missed, attendance_rate, party_loyalty_pct,
                   activity_score
            FROM fct_members WHERE bioguide_id = ?
            """,
            [bioguide_id],
        ).fetchone()
    except Exception:
        row = None

    if row:
        return MemberDetail(
            bioguide_id=row[0], first_name=row[1], last_name=row[2],
            full_name=row[3], party=row[4], state=row[5], district=row[6],
            chamber=row[7], is_current=row[8], image_url=row[9],
            official_url=row[10], leadership_role=row[11], start_date=row[12],
            bills_sponsored=row[13] or 0, bills_enacted=row[14] or 0,
            bills_passed=row[15] or 0, sponsor_success_rate=row[16] or 0,
            votes_cast=row[17] or 0, votes_missed=row[18] or 0,
            attendance_rate=row[19], party_loyalty_pct=row[20],
            activity_score=row[21],
            committees=committees,
            recent_votes=recent_votes,
            recent_bills=recent_bills,
            **contact,
        )

    # Fallback to raw members table
    raw = conn.execute(
        """
        SELECT bioguide_id, first_name, last_name, full_name,
               party, state, district, chamber, is_current,
               image_url, official_url
        FROM members WHERE bioguide_id = ?
        """,
        [bioguide_id],
    ).fetchone()

    if not raw:
        return None

    return MemberDetail(
        **_row_to_member(raw).model_dump(),
        committees=committees, recent_votes=recent_votes,
        recent_bills=recent_bills, **contact,
    )


def _assert_member_exists(conn, bioguide_id: str):
    exists = conn.execute(
        "SELECT 1 FROM members WHERE bioguide_id = ?", [bioguide_id]
    ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")
