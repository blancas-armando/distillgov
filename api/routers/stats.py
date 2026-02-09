"""Stats API endpoints — exposes dbt aggregate views."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CongressSummary(BaseModel):
    congress: int
    total_bills: int
    enacted: int
    passed: int
    in_committee: int
    introduced_only: int
    stale: int
    recently_active: int
    enactment_rate_pct: float | None


class PolicyBreakdown(BaseModel):
    policy_area: str
    congress: int
    total_bills: int
    enacted: int
    passed: int
    in_committee: int
    enactment_rate_pct: float | None


class ChamberComparison(BaseModel):
    chamber: str | None
    congress: int
    total_bills: int
    enacted: int
    passed: int
    avg_days_pending: float | None
    avg_days_to_enactment: float | None


class PartyBreakdown(BaseModel):
    party: str | None
    congress: int
    bills_sponsored: int
    enacted: int
    passed: int
    enactment_rate_pct: float | None


class MemberScorecard(BaseModel):
    bioguide_id: str
    full_name: str | None
    party: str | None
    state: str | None
    chamber: str | None
    bills_sponsored: int
    bills_enacted: int
    bills_passed: int
    sponsor_success_rate: float | None
    votes_cast: int
    votes_missed: int
    attendance_rate: float | None
    party_loyalty_pct: float | None
    activity_score: float | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/congress-summary", response_model=list[CongressSummary])
def congress_summary():
    """High-level bill statistics per Congress."""
    return _query_agg("agg_congress_summary", CongressSummary)


@router.get("/policy-breakdown", response_model=list[PolicyBreakdown])
def policy_breakdown(
    congress: int | None = Query(None, description="Filter by congress number"),
):
    """Bill counts and enactment rates by policy area."""
    where = "WHERE congress = ?" if congress else ""
    params = [congress] if congress else []
    return _query_agg("agg_policy_breakdown", PolicyBreakdown, where, params)


@router.get("/chamber-comparison", response_model=list[ChamberComparison])
def chamber_comparison():
    """House vs Senate bill statistics."""
    return _query_agg("agg_chamber_comparison", ChamberComparison)


@router.get("/party-breakdown", response_model=list[PartyBreakdown])
def party_breakdown():
    """Democratic vs Republican sponsorship and enactment stats."""
    return _query_agg("agg_party_breakdown", PartyBreakdown)


@router.get("/member-scorecard", response_model=list[MemberScorecard])
def member_scorecard(
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    party: str | None = Query(None, description="Filter by party: D, R, I"),
    state: str | None = Query(None, description="Filter by state code"),
    sort: str = Query("bills_sponsored", description="Sort by: bills_sponsored, votes_cast, attendance_rate, party_loyalty_pct"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """Current member rankings by legislative activity."""
    allowed_sorts = {"bills_sponsored", "votes_cast", "attendance_rate", "party_loyalty_pct", "activity_score"}
    if sort not in allowed_sorts:
        raise HTTPException(status_code=400, detail=f"sort must be one of: {', '.join(allowed_sorts)}")

    conditions: list[str] = []
    params: list[object] = []

    if chamber:
        conditions.append("chamber = ?")
        params.append(chamber.lower())
    if party:
        conditions.append("party = ?")
        params.append(party.upper())
    if state:
        conditions.append("state = ?")
        params.append(state.upper())

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    with get_db() as conn:
        try:
            rows = conn.execute(
                f"""
                SELECT bioguide_id, full_name, party, state, chamber,
                       bills_sponsored, bills_enacted, bills_passed, sponsor_success_rate,
                       votes_cast, votes_missed, attendance_rate, party_loyalty_pct,
                       activity_score
                FROM agg_member_scorecard
                {where}
                ORDER BY {sort} DESC NULLS LAST
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()
        except Exception as exc:
            logger.exception("Failed to query agg_member_scorecard")
            raise HTTPException(status_code=503, detail="Scorecard not available — run dbt first") from exc

        return [
            MemberScorecard(
                bioguide_id=r[0], full_name=r[1], party=r[2], state=r[3], chamber=r[4],
                bills_sponsored=r[5], bills_enacted=r[6], bills_passed=r[7],
                sponsor_success_rate=r[8], votes_cast=r[9], votes_missed=r[10],
                attendance_rate=r[11], party_loyalty_pct=r[12], activity_score=r[13],
            )
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_ALLOWED_AGG_TABLES = {
    "agg_congress_summary",
    "agg_policy_breakdown",
    "agg_chamber_comparison",
    "agg_party_breakdown",
    "agg_member_scorecard",
}


def _query_agg(table: str, model: type, where: str = "", params: list | None = None):
    """Generic helper to query an aggregate view and return Pydantic models."""
    if table not in _ALLOWED_AGG_TABLES:
        raise ValueError(f"Unknown aggregate table: {table}")
    with get_db() as conn:
        try:
            rows = conn.execute(
                f"SELECT * FROM {table} {where}", params or []
            ).fetchall()
            columns = [desc[0] for desc in conn.description]
        except Exception as exc:
            logger.exception("Failed to query %s", table)
            raise HTTPException(
                status_code=503,
                detail=f"{table} not available — run dbt first",
            ) from exc

    return [model(**dict(zip(columns, row))) for row in rows]
