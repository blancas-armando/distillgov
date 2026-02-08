"""Members API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.database import get_db

router = APIRouter()


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


class MemberList(BaseModel):
    members: list[Member]
    total: int
    offset: int
    limit: int


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
        # Build query
        conditions = []
        params = []

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

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        total = conn.execute(
            f"SELECT COUNT(*) FROM members WHERE {where_clause}", params
        ).fetchone()[0]

        # Get members
        rows = conn.execute(
            f"""
            SELECT bioguide_id, first_name, last_name, full_name,
                   party, state, district, chamber, is_current,
                   image_url, official_url
            FROM members
            WHERE {where_clause}
            ORDER BY state, last_name
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        members = [
            Member(
                bioguide_id=r[0],
                first_name=r[1],
                last_name=r[2],
                full_name=r[3],
                party=r[4],
                state=r[5],
                district=r[6],
                chamber=r[7],
                is_current=r[8],
                image_url=r[9],
                official_url=r[10],
            )
            for r in rows
        ]

        return MemberList(members=members, total=total, offset=offset, limit=limit)


@router.get("/{bioguide_id}", response_model=Member)
def get_member(bioguide_id: str):
    """Get a single member by bioguide ID."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT bioguide_id, first_name, last_name, full_name,
                   party, state, district, chamber, is_current,
                   image_url, official_url
            FROM members
            WHERE bioguide_id = ?
            """,
            [bioguide_id],
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Member not found")

        return Member(
            bioguide_id=row[0],
            first_name=row[1],
            last_name=row[2],
            full_name=row[3],
            party=row[4],
            state=row[5],
            district=row[6],
            chamber=row[7],
            is_current=row[8],
            image_url=row[9],
            official_url=row[10],
        )
