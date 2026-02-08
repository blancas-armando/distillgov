"""Trades API endpoints."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from datetime import date
from api.database import get_db

router = APIRouter()


class Trade(BaseModel):
    trade_id: str
    bioguide_id: str
    member_name: str | None
    party: str | None
    state: str | None
    chamber: str | None
    transaction_date: date | None
    ticker: str | None
    asset_name: str | None
    trade_type: str | None
    amount_low: int | None
    amount_high: int | None
    owner: str | None


class TradeList(BaseModel):
    trades: list[Trade]
    total: int
    offset: int
    limit: int


@router.get("", response_model=TradeList)
def list_trades(
    ticker: str | None = Query(None, description="Filter by stock ticker"),
    trade_type: str | None = Query(None, description="Filter by type: Purchase, Sale"),
    bioguide_id: str | None = Query(None, description="Filter by member"),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """List recent stock trades by members of Congress."""
    with get_db() as conn:
        conditions = []
        params = []

        if ticker:
            conditions.append("t.ticker = ?")
            params.append(ticker.upper())
        if trade_type:
            conditions.append("t.trade_type = ?")
            params.append(trade_type)
        if bioguide_id:
            conditions.append("t.bioguide_id = ?")
            params.append(bioguide_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        total = conn.execute(
            f"SELECT COUNT(*) FROM trades t WHERE {where_clause}", params
        ).fetchone()[0]

        # Get trades with member info
        rows = conn.execute(
            f"""
            SELECT t.trade_id, t.bioguide_id, m.full_name, m.party, m.state, m.chamber,
                   t.transaction_date, t.ticker, t.asset_name, t.trade_type,
                   t.amount_low, t.amount_high, t.owner
            FROM trades t
            LEFT JOIN members m ON t.bioguide_id = m.bioguide_id
            WHERE {where_clause}
            ORDER BY t.transaction_date DESC NULLS LAST
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

        trades = [
            Trade(
                trade_id=r[0],
                bioguide_id=r[1],
                member_name=r[2],
                party=r[3],
                state=r[4],
                chamber=r[5],
                transaction_date=r[6],
                ticker=r[7],
                asset_name=r[8],
                trade_type=r[9],
                amount_low=r[10],
                amount_high=r[11],
                owner=r[12],
            )
            for r in rows
        ]

        return TradeList(trades=trades, total=total, offset=offset, limit=limit)


@router.get("/by-member/{bioguide_id}", response_model=TradeList)
def get_member_trades(
    bioguide_id: str,
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """Get all trades for a specific member."""
    return list_trades(bioguide_id=bioguide_id, limit=limit, offset=offset)


@router.get("/by-ticker/{ticker}", response_model=TradeList)
def get_ticker_trades(
    ticker: str,
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
):
    """Get all congressional trades for a specific stock ticker."""
    return list_trades(ticker=ticker.upper(), limit=limit, offset=offset)
