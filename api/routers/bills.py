"""Bills API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import escape_like, get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Bill(BaseModel):
    bill_id: str
    congress: int
    bill_type: str
    bill_number: int
    title: str | None
    short_title: str | None
    introduced_date: date | None
    sponsor_id: str | None
    sponsor_name: str | None
    sponsor_party: str | None
    policy_area: str | None
    origin_chamber: str | None
    latest_action: str | None
    latest_action_date: date | None
    status: str | None


class BillDetail(Bill):
    summary: str | None = None
    full_text_url: str | None = None
    subjects: list[str] = []
    total_cosponsors: int = 0
    dem_cosponsors: int = 0
    rep_cosponsors: int = 0
    ind_cosponsors: int = 0


class BillList(BaseModel):
    bills: list[Bill]
    total: int
    offset: int
    limit: int


class Subject(BaseModel):
    name: str
    bill_count: int


class SubjectList(BaseModel):
    subjects: list[Subject]
    total: int


class Category(BaseModel):
    name: str
    bill_count: int


class CategoryList(BaseModel):
    categories: list[Category]


class BillAction(BaseModel):
    action_date: date | None
    action_text: str | None
    action_type: str | None
    chamber: str | None


class BillActionList(BaseModel):
    actions: list[BillAction]
    total: int


class BillVote(BaseModel):
    vote_id: str
    vote_date: date | None
    chamber: str | None
    question: str | None
    result: str | None
    yea_count: int | None
    nay_count: int | None


class BillVoteList(BaseModel):
    votes: list[BillVote]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/categories", response_model=CategoryList)
def list_categories():
    """List all bill policy areas with counts.

    Policy areas come from the Congressional Research Service (CRS) taxonomy.
    Use these values with the `policy_area` filter on the bills list endpoint.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT coalesce(policy_area, 'Unclassified') as name, count(*) as bill_count
            FROM bills
            GROUP BY 1
            ORDER BY bill_count DESC
            """
        ).fetchall()

        return CategoryList(
            categories=[Category(name=r[0], bill_count=r[1]) for r in rows]
        )


@router.get("/subjects", response_model=SubjectList)
def list_subjects(
    q: str | None = Query(None, description="Search subjects by keyword"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Browse all legislative subject tags with bill counts.

    Subjects are more granular than policy areas — a single bill can have
    dozens of subjects. Use these with the `subject` filter on the activity feed
    or member voting record.
    """
    with get_db() as conn:
        conditions = []
        params: list[object] = []

        if q:
            conditions.append("bs.subject ILIKE ? ESCAPE '\\'")
            params.append(f"%{escape_like(q)}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = conn.execute(
            f"SELECT count(DISTINCT subject) FROM bill_subjects bs {where}",
            params,
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT bs.subject, count(*) as bill_count
            FROM bill_subjects bs
            {where}
            GROUP BY bs.subject
            ORDER BY bill_count DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        return SubjectList(
            subjects=[Subject(name=r[0], bill_count=r[1]) for r in rows],
            total=total,
        )


@router.get("", response_model=BillList)
def list_bills(
    q: str | None = Query(None, description="Search bill titles and subjects"),
    subject: str | None = Query(None, description="Filter by exact legislative subject"),
    congress: int | None = Query(None, description="Filter by congress number"),
    status: str | None = Query(None, description="Filter by status"),
    bill_type: str | None = Query(None, description="Filter by type: hr, s, hjres..."),
    policy_area: str | None = Query(None, description="Filter by policy area / category"),
    sponsor_id: str | None = Query(None, description="Filter by sponsor bioguide_id"),
    chamber: str | None = Query(None, description="Filter by origin chamber: house, senate"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """List bills with filtering and search.

    Use `q` to search bill titles and subjects. Use `subject` for exact subject match.
    Use `/api/bills/subjects` to browse available subjects.
    Use `/api/bills/categories` to get valid `policy_area` values.
    """
    with get_db() as conn:
        conditions: list[str] = []
        params: list[object] = []

        if q:
            escaped = escape_like(q)
            conditions.append(
                "(b.title ILIKE ? ESCAPE '\\' OR b.short_title ILIKE ? ESCAPE '\\' "
                "OR b.bill_id IN (SELECT bill_id FROM bill_subjects WHERE subject ILIKE ? ESCAPE '\\'))"
            )
            params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
        if subject:
            conditions.append("b.bill_id IN (SELECT bill_id FROM bill_subjects WHERE subject = ?)")
            params.append(subject)
        if congress:
            conditions.append("b.congress = ?")
            params.append(congress)
        if status:
            conditions.append("b.status = ?")
            params.append(status)
        if bill_type:
            conditions.append("b.bill_type = ?")
            params.append(bill_type.lower())
        if policy_area:
            conditions.append("b.policy_area = ?")
            params.append(policy_area)
        if sponsor_id:
            conditions.append("b.sponsor_id = ?")
            params.append(sponsor_id)
        if chamber:
            conditions.append("b.origin_chamber = ?")
            params.append(chamber.capitalize())

        where = " AND ".join(conditions) if conditions else "1=1"

        total = conn.execute(
            f"SELECT COUNT(*) FROM bills b WHERE {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT b.bill_id, b.congress, b.bill_type, b.bill_number,
                   b.title, b.short_title, b.introduced_date,
                   b.sponsor_id, m.full_name, m.party,
                   b.policy_area, b.origin_chamber,
                   b.latest_action, b.latest_action_date, b.status
            FROM bills b
            LEFT JOIN members m ON b.sponsor_id = m.bioguide_id
            WHERE {where}
            ORDER BY b.latest_action_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        bills = [_row_to_bill(r) for r in rows]
        return BillList(bills=bills, total=total, offset=offset, limit=limit)


@router.get("/{bill_id}", response_model=BillDetail)
def get_bill(bill_id: str):
    """Get a single bill by ID with cosponsorship breakdown."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT b.bill_id, b.congress, b.bill_type, b.bill_number,
                   b.title, b.short_title, b.introduced_date,
                   b.sponsor_id, m.full_name, m.party,
                   b.policy_area, b.origin_chamber,
                   b.latest_action, b.latest_action_date, b.status,
                   b.summary, b.full_text_url
            FROM bills b
            LEFT JOIN members m ON b.sponsor_id = m.bioguide_id
            WHERE b.bill_id = ?
            """,
            [bill_id],
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Bill not found")

        try:
            cosponsor_counts = conn.execute(
                """
                SELECT
                    count(*) as total,
                    count(*) filter (where m.party = 'D') as dem,
                    count(*) filter (where m.party = 'R') as rep,
                    count(*) filter (where m.party not in ('D', 'R')) as ind
                FROM bill_cosponsors c
                LEFT JOIN members m ON c.bioguide_id = m.bioguide_id
                WHERE c.bill_id = ?
                """,
                [bill_id],
            ).fetchone()
        except Exception:
            cosponsor_counts = (0, 0, 0, 0)

        # Get subjects
        try:
            subject_rows = conn.execute(
                "SELECT subject FROM bill_subjects WHERE bill_id = ? ORDER BY subject",
                [bill_id],
            ).fetchall()
            subjects = [r[0] for r in subject_rows]
        except Exception:
            subjects = []

        bill = _row_to_bill(row)
        return BillDetail(
            **bill.model_dump(),
            summary=row[15],
            full_text_url=row[16],
            subjects=subjects,
            total_cosponsors=cosponsor_counts[0],
            dem_cosponsors=cosponsor_counts[1],
            rep_cosponsors=cosponsor_counts[2],
            ind_cosponsors=cosponsor_counts[3],
        )


@router.get("/{bill_id}/actions", response_model=BillActionList)
def get_bill_actions(bill_id: str):
    """Get the action timeline for a bill.

    Shows the progression of a bill through Congress: introduction, committee
    referral, floor votes, passage, signing, etc. Ordered chronologically.
    """
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM bills WHERE bill_id = ?", [bill_id]
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Bill not found")

        rows = conn.execute(
            """
            SELECT action_date, action_text, action_type, chamber
            FROM bill_actions
            WHERE bill_id = ?
            ORDER BY sequence ASC
            """,
            [bill_id],
        ).fetchall()

        actions = [
            BillAction(
                action_date=r[0], action_text=r[1],
                action_type=r[2], chamber=r[3],
            )
            for r in rows
        ]
        return BillActionList(actions=actions, total=len(actions))


@router.get("/{bill_id}/votes", response_model=BillVoteList)
def get_bill_votes(bill_id: str):
    """Get all roll call votes associated with a bill."""
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM bills WHERE bill_id = ?", [bill_id]
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Bill not found")

        rows = conn.execute(
            """
            SELECT vote_id, vote_date, chamber, question, result,
                   yea_count, nay_count
            FROM votes
            WHERE bill_id = ?
            ORDER BY vote_date DESC NULLS LAST
            """,
            [bill_id],
        ).fetchall()

        votes = [
            BillVote(
                vote_id=r[0], vote_date=r[1], chamber=r[2], question=r[3],
                result=r[4], yea_count=r[5], nay_count=r[6],
            )
            for r in rows
        ]
        return BillVoteList(votes=votes, total=len(votes))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_bill(r: tuple) -> Bill:
    return Bill(
        bill_id=r[0], congress=r[1], bill_type=r[2], bill_number=r[3],
        title=r[4], short_title=r[5], introduced_date=r[6],
        sponsor_id=r[7], sponsor_name=r[8], sponsor_party=r[9],
        policy_area=r[10], origin_chamber=r[11],
        latest_action=r[12], latest_action_date=r[13], status=r[14],
    )
