"""Votes API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from api.database import get_db

router = APIRouter()


class Vote(BaseModel):
    vote_id: str
    congress: int
    chamber: str
    roll_call: int
    vote_date: date | None
    question: str | None
    description: str | None
    result: str | None
    bill_id: str | None
    yea_count: int | None
    nay_count: int | None
    present_count: int | None
    not_voting: int | None


class VoteList(BaseModel):
    votes: list[Vote]
    total: int
    offset: int
    limit: int


@router.get("", response_model=VoteList)
def list_votes(
    congress: int | None = Query(None, description="Filter by congress number"),
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    result: str | None = Query(None, description="Filter by result: Passed, Failed"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """List recent roll call votes."""
    with get_db() as conn:
        conditions = []
        params = []

        if congress:
            conditions.append("congress = ?")
            params.append(congress)
        if chamber:
            conditions.append("chamber = ?")
            params.append(chamber.lower())
        if result:
            conditions.append("result = ?")
            params.append(result)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        total = conn.execute(
            f"SELECT COUNT(*) FROM votes WHERE {where_clause}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT vote_id, congress, chamber, roll_call, vote_date,
                   question, description, result, bill_id,
                   yea_count, nay_count, present_count, not_voting
            FROM votes
            WHERE {where_clause}
            ORDER BY vote_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        votes = [
            Vote(
                vote_id=r[0],
                congress=r[1],
                chamber=r[2],
                roll_call=r[3],
                vote_date=r[4],
                question=r[5],
                description=r[6],
                result=r[7],
                bill_id=r[8],
                yea_count=r[9],
                nay_count=r[10],
                present_count=r[11],
                not_voting=r[12],
            )
            for r in rows
        ]

        return VoteList(votes=votes, total=total, offset=offset, limit=limit)


@router.get("/{vote_id}", response_model=Vote)
def get_vote(vote_id: str):
    """Get a single vote by ID."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT vote_id, congress, chamber, roll_call, vote_date,
                   question, description, result, bill_id,
                   yea_count, nay_count, present_count, not_voting
            FROM votes
            WHERE vote_id = ?
            """,
            [vote_id],
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Vote not found")

        return Vote(
            vote_id=row[0],
            congress=row[1],
            chamber=row[2],
            roll_call=row[3],
            vote_date=row[4],
            question=row[5],
            description=row[6],
            result=row[7],
            bill_id=row[8],
            yea_count=row[9],
            nay_count=row[10],
            present_count=row[11],
            not_voting=row[12],
        )
