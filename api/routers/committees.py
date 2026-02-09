"""Committees API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import escape_like, get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CommitteeMember(BaseModel):
    bioguide_id: str
    full_name: str | None
    party: str | None
    state: str | None
    chamber: str | None
    role: str | None
    image_url: str | None


class Committee(BaseModel):
    committee_id: str
    name: str
    chamber: str | None
    committee_type: str | None
    parent_id: str | None
    url: str | None
    member_count: int = 0


class CommitteeDetail(Committee):
    members: list[CommitteeMember] = []


class CommitteeList(BaseModel):
    committees: list[Committee]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=CommitteeList)
def list_committees(
    q: str | None = Query(None, description="Search committees by name"),
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List congressional committees with member counts."""
    with get_db() as conn:
        conditions: list[str] = []
        params: list[object] = []

        if q:
            conditions.append("c.name ILIKE ? ESCAPE '\\'")
            params.append(f"%{escape_like(q)}%")
        if chamber:
            conditions.append("c.chamber = ?")
            params.append(chamber.lower())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        total = conn.execute(
            f"SELECT count(*) FROM committees c {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT c.committee_id, c.name, c.chamber, c.committee_type,
                   c.parent_id, c.url,
                   coalesce(cm_counts.member_count, 0) as member_count
            FROM committees c
            LEFT JOIN (
                SELECT committee_id, count(*) as member_count
                FROM committee_members
                GROUP BY committee_id
            ) cm_counts ON cm_counts.committee_id = c.committee_id
            {where}
            ORDER BY c.name
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        committees = [
            Committee(
                committee_id=r[0], name=r[1], chamber=r[2],
                committee_type=r[3], parent_id=r[4], url=r[5],
                member_count=r[6],
            )
            for r in rows
        ]
        return CommitteeList(committees=committees, total=total, offset=offset, limit=limit)


@router.get("/{committee_id}", response_model=CommitteeDetail)
def get_committee(committee_id: str):
    """Get a committee with its full member list."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT c.committee_id, c.name, c.chamber, c.committee_type,
                   c.parent_id, c.url
            FROM committees c
            WHERE c.committee_id = ?
            """,
            [committee_id],
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Committee not found")

        member_rows = conn.execute(
            """
            SELECT cm.bioguide_id, m.full_name, m.party, m.state, m.chamber,
                   cm.role, m.image_url
            FROM committee_members cm
            JOIN members m ON cm.bioguide_id = m.bioguide_id
            WHERE cm.committee_id = ?
            ORDER BY
                CASE cm.role
                    WHEN 'Chair' THEN 1
                    WHEN 'Ranking Member' THEN 2
                    WHEN 'Vice Chair' THEN 3
                    ELSE 4
                END,
                m.last_name
            """,
            [committee_id],
        ).fetchall()

        members = [
            CommitteeMember(
                bioguide_id=r[0], full_name=r[1], party=r[2],
                state=r[3], chamber=r[4], role=r[5], image_url=r[6],
            )
            for r in member_rows
        ]

        return CommitteeDetail(
            committee_id=row[0], name=row[1], chamber=row[2],
            committee_type=row[3], parent_id=row[4], url=row[5],
            member_count=len(members), members=members,
        )
