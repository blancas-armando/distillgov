"""Sync stock trades from congressional disclosures using CapitolGains."""

from __future__ import annotations

import duckdb
import hashlib
from rich.console import Console
from rich.progress import track

from capitolgains import Representative, Senator
from capitolgains.utils.representative_scraper import HouseDisclosureScraper
from capitolgains.utils.senator_scraper import SenateDisclosureScraper

from config import DB_PATH

console = Console()

# State name to code mapping
STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
    "Puerto Rico": "PR", "Guam": "GU", "American Samoa": "AS",
    "U.S. Virgin Islands": "VI", "Northern Mariana Islands": "MP",
}


def get_state_code(state: str) -> str | None:
    """Convert state name to state code."""
    if not state:
        return None
    if len(state) == 2 and state.upper() in STATE_CODES.values():
        return state.upper()
    return STATE_CODES.get(state)


def generate_trade_id(bioguide_id: str, pdf_url: str) -> str:
    """Generate a unique trade ID from bioguide and PDF URL."""
    raw = f"{bioguide_id}-{pdf_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def sync_house_trades(year: int, conn: duckdb.DuckDBPyConnection) -> int:
    """Sync House member trades (PTR filings)."""
    console.print(f"[blue]Syncing House disclosures for {year}...[/blue]")

    members = conn.execute(
        "SELECT bioguide_id, first_name, last_name, state, district FROM members WHERE chamber = 'house' AND is_current = TRUE"
    ).fetchall()

    if not members:
        console.print("[yellow]No House members found. Run 'sync members' first.[/yellow]")
        return 0

    inserted = 0
    checked = 0

    with HouseDisclosureScraper() as scraper:
        for bioguide_id, first_name, last_name, state, district in track(
            members, description="Fetching House disclosures..."
        ):
            checked += 1
            try:
                state_code = get_state_code(state)
                if not state_code:
                    continue

                rep = Representative(last_name, state=state_code, district=str(district) if district else None)
                disclosures = rep.get_disclosures(scraper, year=str(year))

                # CapitolGains returns PTR filings, not individual trades
                filings = disclosures.get("trades", [])
                for filing in filings:
                    pdf_url = filing.get("pdf_url", "")
                    if not pdf_url:
                        continue

                    trade_id = generate_trade_id(bioguide_id, pdf_url)
                    filing_type = filing.get("filing_type", "ptr")

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO trades (
                            trade_id, bioguide_id, asset_name, trade_type,
                            ptr_link, comment, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        [
                            trade_id,
                            bioguide_id,
                            f"PTR Filing - {filing_type}",
                            "disclosure",
                            pdf_url,
                            f"Year: {filing.get('year')}",
                        ],
                    )
                    inserted += 1

            except Exception as e:
                # Silently skip members without disclosures
                if "No disclosure" not in str(e) and "not found" not in str(e).lower():
                    console.print(f"[dim]  {first_name} {last_name}: {e}[/dim]")
                continue

    console.print(f"  Checked {checked} House members")
    return inserted


def sync_senate_trades(year: int, conn: duckdb.DuckDBPyConnection) -> int:
    """Sync Senate member trades (PTR filings)."""
    console.print(f"[blue]Syncing Senate disclosures for {year}...[/blue]")

    members = conn.execute(
        "SELECT bioguide_id, first_name, last_name, state FROM members WHERE chamber = 'senate' AND is_current = TRUE"
    ).fetchall()

    if not members:
        console.print("[yellow]No Senators found. Run 'sync members' first.[/yellow]")
        return 0

    inserted = 0
    checked = 0

    with SenateDisclosureScraper() as scraper:
        for bioguide_id, first_name, last_name, state in track(
            members, description="Fetching Senate disclosures..."
        ):
            checked += 1
            try:
                state_code = get_state_code(state)
                if not state_code:
                    continue

                senator = Senator(last_name, first_name=first_name, state=state_code)
                disclosures = senator.get_disclosures(scraper, year=str(year))

                filings = disclosures.get("trades", [])
                for filing in filings:
                    pdf_url = filing.get("pdf_url", "")
                    if not pdf_url:
                        continue

                    trade_id = generate_trade_id(bioguide_id, pdf_url)
                    filing_type = filing.get("filing_type", "ptr")

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO trades (
                            trade_id, bioguide_id, asset_name, trade_type,
                            ptr_link, comment, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        [
                            trade_id,
                            bioguide_id,
                            f"PTR Filing - {filing_type}",
                            "disclosure",
                            pdf_url,
                            f"Year: {filing.get('year')}",
                        ],
                    )
                    inserted += 1

            except Exception as e:
                if "No disclosure" not in str(e) and "not found" not in str(e).lower():
                    console.print(f"[dim]  {first_name} {last_name}: {e}[/dim]")
                continue

    console.print(f"  Checked {checked} Senators")
    return inserted


def sync_trades(year: int = 2024):
    """Sync all congressional stock trade disclosures for a given year."""
    conn = duckdb.connect(str(DB_PATH))

    house_count = sync_house_trades(year, conn)
    senate_count = sync_senate_trades(year, conn)

    conn.close()

    total = house_count + senate_count
    console.print(f"[green]Inserted {total} disclosure filings ({house_count} House, {senate_count} Senate)[/green]")


if __name__ == "__main__":
    sync_trades()
