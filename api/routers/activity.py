"""Activity feed — what's happening in Congress right now."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.database import escape_like, get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ActivityItem(BaseModel):
    event_type: str        # "vote", "introduced", "enacted", "signed"
    date: date | None
    title: str
    description: str | None = None
    bill_id: str | None = None
    vote_id: str | None = None
    chamber: str | None = None
    policy_area: str | None = None
    result: str | None = None


class ActivityFeed(BaseModel):
    items: list[ActivityItem]
    total: int
    offset: int
    limit: int
    next_cursor: date | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/recent", response_model=ActivityFeed)
def recent_activity(
    subject: str | None = Query(None, description="Filter by legislative subject"),
    policy_area: str | None = Query(None, description="Filter by policy area"),
    member: str | None = Query(None, description="Filter by member bioguide_id (their votes and sponsored bills)"),
    zip_code: str | None = Query(None, description="Filter by zip code (activity from your reps)"),
    chamber: str | None = Query(None, description="Filter by chamber: house, senate"),
    days: int = Query(30, ge=1, le=365, description="Look back this many days"),
    before: date | None = Query(None, description="Cursor: only show events before this date (preferred over offset)"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """What's happening in Congress right now.

    Returns a unified, chronological feed of recent votes, bill introductions,
    and enactments. Filter by topic, member, or zip code to see what matters to you.

    Event types:
    - **vote**: A roll call vote was held (passage, amendment, procedural)
    - **introduced**: A new bill was introduced
    - **enacted**: A bill became law
    """
    with get_db() as conn:
        # If zip_code provided, resolve to member IDs
        member_ids: list[str] = []
        if zip_code:
            if len(zip_code) != 5 or not zip_code.isdigit():
                raise HTTPException(status_code=400, detail="Zip code must be 5 digits")
            rows = conn.execute(
                """
                SELECT DISTINCT m.bioguide_id
                FROM zip_districts z
                JOIN members m ON z.state = m.state AND z.district = m.district AND m.chamber = 'house'
                WHERE z.zcta = ? AND m.is_current = TRUE
                UNION
                SELECT m.bioguide_id
                FROM members m
                WHERE m.state = (SELECT z.state FROM zip_districts z WHERE z.zcta = ? LIMIT 1)
                  AND m.chamber = 'senate' AND m.is_current = TRUE
                """,
                [zip_code, zip_code],
            ).fetchall()
            member_ids = [r[0] for r in rows]
            if not member_ids:
                raise HTTPException(status_code=404, detail="No representatives found for this zip code")
        elif member:
            member_ids = [member]

        # Build the subject filter join
        subject_join = ""
        subject_condition = ""
        subject_params: list[object] = []
        if subject:
            subject_join = "JOIN bill_subjects bs ON b.bill_id = bs.bill_id"
            subject_condition = "AND bs.subject ILIKE ? ESCAPE '\\'"
            subject_params = [f"%{escape_like(subject)}%"]

        policy_condition = ""
        policy_params: list[object] = []
        if policy_area:
            policy_condition = "AND b.policy_area = ?"
            policy_params = [policy_area]

        chamber_condition = ""
        chamber_params: list[object] = []
        if chamber:
            chamber_condition = "AND chamber = ?"
            chamber_params = [chamber.lower()]

        # Member filter for votes
        member_vote_condition = ""
        member_vote_params: list[object] = []
        if member_ids:
            placeholders = ", ".join(["?"] * len(member_ids))
            member_vote_condition = f"AND v.vote_id IN (SELECT vote_id FROM member_votes WHERE bioguide_id IN ({placeholders}))"
            member_vote_params = list(member_ids)

        # Member filter for bills
        member_bill_condition = ""
        member_bill_params: list[object] = []
        if member_ids:
            placeholders = ", ".join(["?"] * len(member_ids))
            member_bill_condition = f"AND (b.sponsor_id IN ({placeholders}) OR b.bill_id IN (SELECT bill_id FROM bill_cosponsors WHERE bioguide_id IN ({placeholders})))"
            member_bill_params = list(member_ids) + list(member_ids)

        # Keyset cursor filter
        cursor_vote_condition = ""
        cursor_vote_params: list[object] = []
        cursor_intro_condition = ""
        cursor_intro_params: list[object] = []
        cursor_enacted_condition = ""
        cursor_enacted_params: list[object] = []
        if before:
            cursor_vote_condition = "AND v.vote_date < ?"
            cursor_vote_params = [before]
            cursor_intro_condition = "AND b.introduced_date < ?"
            cursor_intro_params = [before]
            cursor_enacted_condition = "AND b.latest_action_date < ?"
            cursor_enacted_params = [before]

        # Votes feed
        votes_query = f"""
            SELECT 'vote' as event_type, v.vote_date as date,
                   coalesce(b.title, v.question, 'Roll Call Vote') as title,
                   v.result as description,
                   v.bill_id, v.vote_id, v.chamber, b.policy_area, v.result
            FROM votes v
            LEFT JOIN bills b ON v.bill_id = b.bill_id
            {subject_join}
            WHERE v.vote_date >= current_date - interval '{days} days'
            {cursor_vote_condition}
            {subject_condition}
            {policy_condition}
            {chamber_condition.replace("chamber", "v.chamber")}
            {member_vote_condition}
        """

        # Bills introduced feed
        bills_intro_query = f"""
            SELECT 'introduced' as event_type, b.introduced_date as date,
                   b.title, b.policy_area as description,
                   b.bill_id, NULL as vote_id, b.origin_chamber as chamber,
                   b.policy_area, NULL as result
            FROM bills b
            {subject_join}
            WHERE b.introduced_date >= current_date - interval '{days} days'
            {cursor_intro_condition}
            {subject_condition}
            {policy_condition}
            {chamber_condition.replace("chamber", "b.origin_chamber") if chamber else ""}
            {member_bill_condition}
        """

        # Bills enacted feed
        enacted_query = f"""
            SELECT 'enacted' as event_type, b.latest_action_date as date,
                   b.title, 'Signed into law' as description,
                   b.bill_id, NULL as vote_id, b.origin_chamber as chamber,
                   b.policy_area, NULL as result
            FROM bills b
            {subject_join}
            WHERE b.status = 'enacted'
              AND b.latest_action_date >= current_date - interval '{days} days'
            {cursor_enacted_condition}
            {subject_condition}
            {policy_condition}
            {member_bill_condition}
        """

        # Combine all params in order
        votes_params: list[object] = []
        votes_params.extend(cursor_vote_params)
        if subject:
            votes_params.extend(subject_params)
        if policy_area:
            votes_params.extend(policy_params)
        if chamber:
            votes_params.extend(chamber_params)
        votes_params.extend(member_vote_params)

        intro_params: list[object] = []
        intro_params.extend(cursor_intro_params)
        if subject:
            intro_params.extend(subject_params)
        if policy_area:
            intro_params.extend(policy_params)
        if chamber:
            intro_params.extend(chamber_params)
        intro_params.extend(member_bill_params)

        enacted_params: list[object] = []
        enacted_params.extend(cursor_enacted_params)
        if subject:
            enacted_params.extend(subject_params)
        if policy_area:
            enacted_params.extend(policy_params)
        enacted_params.extend(member_bill_params)

        # When using keyset cursor, omit OFFSET
        use_offset = not before
        offset_clause = "OFFSET ?" if use_offset else ""

        combined_query = f"""
            SELECT * FROM (
                {votes_query}
                UNION ALL
                {bills_intro_query}
                UNION ALL
                {enacted_query}
            )
            ORDER BY date DESC NULLS LAST
            LIMIT ? {offset_clause}
        """

        pagination_params: list[object] = [limit]
        if use_offset:
            pagination_params.append(offset)

        all_params = votes_params + intro_params + enacted_params + pagination_params

        rows = conn.execute(combined_query, all_params).fetchall()

        # Count total
        count_query = f"""
            SELECT count(*) FROM (
                {votes_query}
                UNION ALL
                {bills_intro_query}
                UNION ALL
                {enacted_query}
            )
        """
        count_params = votes_params + intro_params + enacted_params
        total = conn.execute(count_query, count_params).fetchone()[0]

        items = [
            ActivityItem(
                event_type=r[0], date=r[1], title=r[2] or "Untitled",
                description=r[3], bill_id=r[4], vote_id=r[5],
                chamber=r[6], policy_area=r[7], result=r[8],
            )
            for r in rows
        ]

        # Derive next_cursor from the last item's date
        next_cursor = items[-1].date if items else None

        return ActivityFeed(
            items=items, total=total, offset=offset, limit=limit,
            next_cursor=next_cursor,
        )


@router.get("/trending-subjects", response_model=list[dict])
def trending_subjects(
    days: int = Query(30, ge=1, le=365, description="Look back this many days"),
    limit: int = Query(20, ge=1, le=100),
):
    """Subjects with the most activity in the recent period.

    Returns subjects ranked by the number of bills introduced or voted on
    in the given timeframe. Use these to understand what Congress is focused on.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT bs.subject, count(DISTINCT bs.bill_id) as bill_count
            FROM bill_subjects bs
            JOIN bills b ON bs.bill_id = b.bill_id
            WHERE b.latest_action_date >= current_date - interval ? day
            GROUP BY bs.subject
            ORDER BY bill_count DESC
            LIMIT ?
            """,
            [days, limit],
        ).fetchall()

        return [{"subject": r[0], "bill_count": r[1]} for r in rows]
