"""Sync stock trades from congressional disclosures using CapitolGains."""

import duckdb
import hashlib
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.progress import track

from capitolgains import Representative, Senator
from capitolgains.utils.representative_scraper import HouseDisclosureScraper
from capitolgains.utils.senator_scraper import SenateDisclosureScraper

console = Console()
DB_PATH = Path(__file__).parent.parent / "db" / "distillgov.duckdb"


def parse_amount_range(amount_str: str) -> tuple[int | None, int | None]:
    """Parse amount range string like '$1,001 - $15,000' into (low, high)."""
    if not amount_str or amount_str == "--":
        return None, None

    # Remove $ and commas
    clean = amount_str.replace("$", "").replace(",", "")

    if " - " in clean:
        parts = clean.split(" - ")
        try:
            low = int(parts[0].strip())
            high = int(parts[1].strip())
            return low, high
        except ValueError:
            return None, None
    else:
        try:
            val = int(clean.strip())
            return val, val
        except ValueError:
            return None, None


def generate_trade_id(bioguide_id: str, transaction_date: str, ticker: str, trade_type: str) -> str:
    """Generate a unique trade ID."""
    raw = f"{bioguide_id}-{transaction_date}-{ticker}-{trade_type}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def sync_house_trades(year: int, conn: duckdb.DuckDBPyConnection) -> int:
    """Sync House member trades."""
    console.print(f"[blue]Syncing House trades for {year}...[/blue]")

    # Get current House members from our database
    members = conn.execute(
        "SELECT bioguide_id, first_name, last_name, state, district FROM members WHERE chamber = 'house' AND is_current = TRUE"
    ).fetchall()

    if not members:
        console.print("[yellow]No House members found. Run 'sync members' first.[/yellow]")
        return 0

    inserted = 0

    with HouseDisclosureScraper() as scraper:
        for bioguide_id, first_name, last_name, state, district in track(
            members, description="Fetching House disclosures..."
        ):
            try:
                rep = Representative(last_name, state=state, district=str(district) if district else None)
                disclosures = rep.get_disclosures(scraper, year=str(year))

                trades = disclosures.get("trades", [])
                for trade in trades:
                    trade_id = generate_trade_id(
                        bioguide_id,
                        trade.get("transaction_date", ""),
                        trade.get("ticker", ""),
                        trade.get("type", ""),
                    )

                    amount_low, amount_high = parse_amount_range(trade.get("amount", ""))

                    # Parse dates
                    trans_date = None
                    if trade.get("transaction_date"):
                        try:
                            trans_date = datetime.strptime(
                                trade["transaction_date"], "%m/%d/%Y"
                            ).date()
                        except ValueError:
                            pass

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO trades (
                            trade_id, bioguide_id, transaction_date, ticker,
                            asset_name, asset_type, trade_type,
                            amount_low, amount_high, owner, ptr_link,
                            comment, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        [
                            trade_id,
                            bioguide_id,
                            trans_date,
                            trade.get("ticker"),
                            trade.get("asset_description"),
                            trade.get("asset_type"),
                            trade.get("type"),
                            amount_low,
                            amount_high,
                            trade.get("owner"),
                            trade.get("ptr_link"),
                            trade.get("comment"),
                        ],
                    )
                    inserted += 1

            except Exception as e:
                console.print(f"[dim]  Skipped {first_name} {last_name}: {e}[/dim]")
                continue

    return inserted


def sync_senate_trades(year: int, conn: duckdb.DuckDBPyConnection) -> int:
    """Sync Senate member trades."""
    console.print(f"[blue]Syncing Senate trades for {year}...[/blue]")

    # Get current Senators from our database
    members = conn.execute(
        "SELECT bioguide_id, first_name, last_name, state FROM members WHERE chamber = 'senate' AND is_current = TRUE"
    ).fetchall()

    if not members:
        console.print("[yellow]No Senators found. Run 'sync members' first.[/yellow]")
        return 0

    inserted = 0

    with SenateDisclosureScraper() as scraper:
        for bioguide_id, first_name, last_name, state in track(
            members, description="Fetching Senate disclosures..."
        ):
            try:
                senator = Senator(last_name, first_name=first_name, state=state)
                disclosures = senator.get_disclosures(scraper, year=str(year))

                trades = disclosures.get("trades", [])
                for trade in trades:
                    trade_id = generate_trade_id(
                        bioguide_id,
                        trade.get("transaction_date", ""),
                        trade.get("ticker", ""),
                        trade.get("type", ""),
                    )

                    amount_low, amount_high = parse_amount_range(trade.get("amount", ""))

                    # Parse dates
                    trans_date = None
                    if trade.get("transaction_date"):
                        try:
                            trans_date = datetime.strptime(
                                trade["transaction_date"], "%m/%d/%Y"
                            ).date()
                        except ValueError:
                            pass

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO trades (
                            trade_id, bioguide_id, transaction_date, ticker,
                            asset_name, asset_type, trade_type,
                            amount_low, amount_high, owner, ptr_link,
                            comment, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        [
                            trade_id,
                            bioguide_id,
                            trans_date,
                            trade.get("ticker"),
                            trade.get("asset_description"),
                            trade.get("asset_type"),
                            trade.get("type"),
                            amount_low,
                            amount_high,
                            trade.get("owner"),
                            trade.get("ptr_link"),
                            trade.get("comment"),
                        ],
                    )
                    inserted += 1

            except Exception as e:
                console.print(f"[dim]  Skipped {first_name} {last_name}: {e}[/dim]")
                continue

    return inserted


def sync_trades(year: int = 2024):
    """Sync all congressional stock trades for a given year."""
    conn = duckdb.connect(str(DB_PATH))

    house_count = sync_house_trades(year, conn)
    senate_count = sync_senate_trades(year, conn)

    conn.close()

    total = house_count + senate_count
    console.print(f"[green]Inserted {total} trades ({house_count} House, {senate_count} Senate)[/green]")


if __name__ == "__main__":
    sync_trades()
