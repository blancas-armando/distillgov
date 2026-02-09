"""Votes API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


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


class MemberPosition(BaseModel):
    bioguide_id: str
    full_name: str | None
    party: str | None
    state: str | None
    position: str


class PartyTally(BaseModel):
    party: str
    yes: int
    no: int
    present: int
    not_voting: int
    total: int


class VotePositions(BaseModel):
    vote_id: str
    question: str | None
    result: str | None
    bill_id: str | None
    party_breakdown: list[PartyTally]
    positions: list[MemberPosition]
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=VoteList)
def list_votes(
    congress: int | None = Query(None, description="Filter by congress number"),
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    result: str | None = Query(None, description="Filter by result: Passed, Failed"),
    bill_id: str | None = Query(None, description="Filter by linked bill_id"),
    passage_only: bool = Query(False, description="Only show passage/substantive votes (exclude procedural)"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """List recent roll call votes.

    Use `passage_only=true` to filter out procedural votes and only see
    final passage, conference reports, veto overrides, and other substantive votes.
    """
    with get_db() as conn:
        conditions: list[str] = []
        params: list[object] = []

        if congress:
            conditions.append("congress = ?")
            params.append(congress)
        if chamber:
            conditions.append("chamber = ?")
            params.append(chamber.lower())
        if result:
            conditions.append("result = ?")
            params.append(result)
        if bill_id:
            conditions.append("bill_id = ?")
            params.append(bill_id)
        if passage_only:
            conditions.append(
                "(question ILIKE '%passage%' OR question ILIKE '%pass%' "
                "OR question ILIKE '%conference report%' OR question ILIKE '%override%' "
                "OR question ILIKE '%concur%' OR question ILIKE '%adopt%' "
                "OR question ILIKE '%ratif%')"
            )

        where = " AND ".join(conditions) if conditions else "1=1"

        total = conn.execute(
            f"SELECT COUNT(*) FROM votes WHERE {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT vote_id, congress, chamber, roll_call, vote_date,
                   question, description, result, bill_id,
                   yea_count, nay_count, present_count, not_voting
            FROM votes
            WHERE {where}
            ORDER BY vote_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        votes = [_row_to_vote(r) for r in rows]
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

        return _row_to_vote(row)


@router.get("/{vote_id}/positions", response_model=VotePositions)
def get_vote_positions(
    vote_id: str,
    party: str | None = Query(None, description="Filter by party: D, R, I"),
    position: str | None = Query(None, description="Filter by position: Yes, No, Not Voting, Present"),
):
    """Get individual member positions for a roll call vote.

    Returns every member's vote along with a party breakdown summary.
    The party_breakdown shows how many from each party voted Yes/No/Present/Not Voting.
    """
    with get_db() as conn:
        # Verify vote exists and get metadata
        vote_row = conn.execute(
            "SELECT vote_id, question, result, bill_id FROM votes WHERE vote_id = ?",
            [vote_id],
        ).fetchone()

        if not vote_row:
            raise HTTPException(status_code=404, detail="Vote not found")

        # Build filters for positions query
        conditions = ["mv.vote_id = ?"]
        params: list[object] = [vote_id]

        if party:
            conditions.append("m.party = ?")
            params.append(party.upper())
        if position:
            conditions.append("mv.position = ?")
            params.append(position)

        where = " AND ".join(conditions)

        # Individual positions
        rows = conn.execute(
            f"""
            SELECT mv.bioguide_id, m.full_name, m.party, m.state, mv.position
            FROM member_votes mv
            LEFT JOIN members m ON mv.bioguide_id = m.bioguide_id
            WHERE {where}
            ORDER BY m.party, m.state, m.last_name
            """,
            params,
        ).fetchall()

        positions = [
            MemberPosition(
                bioguide_id=r[0], full_name=r[1], party=r[2],
                state=r[3], position=r[4],
            )
            for r in rows
        ]

        # Party breakdown (always unfiltered to show full picture)
        tally_rows = conn.execute(
            """
            SELECT
                coalesce(m.party, '?') as party,
                count(*) filter (where mv.position in ('Yes', 'Yea')) as yes,
                count(*) filter (where mv.position in ('No', 'Nay')) as no,
                count(*) filter (where mv.position = 'Present') as present,
                count(*) filter (where mv.position = 'Not Voting') as not_voting,
                count(*) as total
            FROM member_votes mv
            LEFT JOIN members m ON mv.bioguide_id = m.bioguide_id
            WHERE mv.vote_id = ?
            GROUP BY 1
            ORDER BY total DESC
            """,
            [vote_id],
        ).fetchall()

        party_breakdown = [
            PartyTally(
                party=r[0], yes=r[1], no=r[2],
                present=r[3], not_voting=r[4], total=r[5],
            )
            for r in tally_rows
        ]

        return VotePositions(
            vote_id=vote_row[0],
            question=vote_row[1],
            result=vote_row[2],
            bill_id=vote_row[3],
            party_breakdown=party_breakdown,
            positions=positions,
            total=len(positions),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_vote(r: tuple) -> Vote:
    return Vote(
        vote_id=r[0], congress=r[1], chamber=r[2], roll_call=r[3],
        vote_date=r[4], question=r[5], description=r[6], result=r[7],
        bill_id=r[8], yea_count=r[9], nay_count=r[10],
        present_count=r[11], not_voting=r[12],
    )
