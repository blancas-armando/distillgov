"""Bills API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import date
from api.database import get_db

router = APIRouter()


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


class BillList(BaseModel):
    bills: list[Bill]
    total: int
    offset: int
    limit: int


@router.get("", response_model=BillList)
def list_bills(
    congress: int | None = Query(None, description="Filter by congress number"),
    status: str | None = Query(None, description="Filter by status"),
    bill_type: str | None = Query(None, description="Filter by type: hr, s, hjres..."),
    policy_area: str | None = Query(None, description="Filter by policy area"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """List bills."""
    with get_db() as conn:
        conditions = []
        params = []

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

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        total = conn.execute(
            f"SELECT COUNT(*) FROM bills b WHERE {where_clause}", params
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
            WHERE {where_clause}
            ORDER BY b.latest_action_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        bills = [
            Bill(
                bill_id=r[0],
                congress=r[1],
                bill_type=r[2],
                bill_number=r[3],
                title=r[4],
                short_title=r[5],
                introduced_date=r[6],
                sponsor_id=r[7],
                sponsor_name=r[8],
                sponsor_party=r[9],
                policy_area=r[10],
                origin_chamber=r[11],
                latest_action=r[12],
                latest_action_date=r[13],
                status=r[14],
            )
            for r in rows
        ]

        return BillList(bills=bills, total=total, offset=offset, limit=limit)


@router.get("/{bill_id}", response_model=Bill)
def get_bill(bill_id: str):
    """Get a single bill by ID."""
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT b.bill_id, b.congress, b.bill_type, b.bill_number,
                   b.title, b.short_title, b.introduced_date,
                   b.sponsor_id, m.full_name, m.party,
                   b.policy_area, b.origin_chamber,
                   b.latest_action, b.latest_action_date, b.status
            FROM bills b
            LEFT JOIN members m ON b.sponsor_id = m.bioguide_id
            WHERE b.bill_id = ?
            """,
            [bill_id],
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Bill not found")

        return Bill(
            bill_id=row[0],
            congress=row[1],
            bill_type=row[2],
            bill_number=row[3],
            title=row[4],
            short_title=row[5],
            introduced_date=row[6],
            sponsor_id=row[7],
            sponsor_name=row[8],
            sponsor_party=row[9],
            policy_area=row[10],
            origin_chamber=row[11],
            latest_action=row[12],
            latest_action_date=row[13],
            status=row[14],
        )
