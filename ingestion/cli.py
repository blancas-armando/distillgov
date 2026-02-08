"""CLI for distillgov data ingestion."""

from __future__ import annotations

import typer
from rich.console import Console

from config import DB_PATH, SCHEMA_PATH, FACTS_PATH

app = typer.Typer(help="Distillgov data ingestion CLI")
console = Console()


@app.command()
def init():
    """Initialize the DuckDB database with schema."""
    import duckdb

    console.print("[bold blue]Initializing database...[/bold blue]")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(DB_PATH))
    schema_sql = SCHEMA_PATH.read_text()
    conn.execute(schema_sql)
    conn.close()

    console.print(f"[bold green]Database initialized at {DB_PATH}[/bold green]")


@app.command()
def sync(
    target: str = typer.Argument(..., help="What to sync: members, bills, cosponsors, actions, votes, member-votes, trades, all"),
    congress: int = typer.Option(118, help="Congress number (e.g., 118 for 118th Congress)"),
    year: int = typer.Option(2024, help="Year for trades sync"),
):
    """Sync data from sources into DuckDB.

    Targets:
      members       - Members of Congress
      bills         - Bills and resolutions
      cosponsors    - Bill cosponsors (requires bills)
      actions       - Bill action timelines (requires bills)
      votes         - Roll call votes (House only)
      member-votes  - Individual member voting positions (requires votes)
      trades        - Stock trading disclosures
      all           - Sync members, bills, votes (not cosponsors/actions/member-votes due to API limits)
    """
    if target == "all":
        targets = ["members", "bills", "votes"]
    else:
        targets = [target]

    for t in targets:
        console.print(f"\n[bold blue]Syncing {t}...[/bold blue]")

        if t == "members":
            from ingestion.sync_members import sync_members
            sync_members(congress=congress)

        elif t == "bills":
            from ingestion.sync_bills import sync_bills
            sync_bills(congress=congress)

        elif t == "cosponsors":
            from ingestion.sync_bills import sync_cosponsors
            sync_cosponsors(congress=congress)

        elif t == "actions":
            from ingestion.sync_bills import sync_actions
            sync_actions(congress=congress)

        elif t == "votes":
            from ingestion.sync_votes import sync_votes
            sync_votes(congress=congress)

        elif t == "member-votes":
            from ingestion.sync_votes import sync_member_votes
            sync_member_votes(congress=congress)

        elif t == "trades":
            from ingestion.sync_trades import sync_trades
            sync_trades(year=year)

        else:
            console.print(f"[red]Unknown target: {t}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]Completed {t}[/green]")


@app.command()
def rebuild_facts():
    """Rebuild fact tables and views from base data."""
    import duckdb

    if not DB_PATH.exists():
        console.print("[red]Database not found. Run 'init' first.[/red]")
        raise typer.Exit(1)

    if not FACTS_PATH.exists():
        console.print("[red]facts.sql not found.[/red]")
        raise typer.Exit(1)

    console.print("[bold blue]Rebuilding fact tables...[/bold blue]")

    conn = duckdb.connect(str(DB_PATH))
    facts_sql = FACTS_PATH.read_text()
    conn.execute(facts_sql)

    # Show counts
    bill_facts = conn.execute("SELECT COUNT(*) FROM bill_facts").fetchone()[0]
    member_facts = conn.execute("SELECT COUNT(*) FROM member_facts").fetchone()[0]
    conn.close()

    console.print(f"  bill_facts: [cyan]{bill_facts:,}[/cyan] rows")
    console.print(f"  member_facts: [cyan]{member_facts:,}[/cyan] rows")
    console.print("[bold green]Fact tables rebuilt[/bold green]")


@app.command()
def stats():
    """Show database statistics."""
    import duckdb

    if not DB_PATH.exists():
        console.print("[red]Database not found. Run 'init' first.[/red]")
        raise typer.Exit(1)

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    console.print("\n[bold]Base Tables[/bold]\n")
    base_tables = ["members", "bills", "bill_cosponsors", "bill_actions", "votes", "member_votes", "trades", "committees"]
    for table in base_tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            console.print(f"  {table}: [cyan]{count:,}[/cyan] rows")
        except Exception:
            console.print(f"  {table}: [dim]not found[/dim]")

    console.print("\n[bold]Fact Tables[/bold]\n")
    fact_tables = ["bill_facts", "member_facts"]
    for table in fact_tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            console.print(f"  {table}: [cyan]{count:,}[/cyan] rows")
        except Exception:
            console.print(f"  {table}: [dim]not built (run 'rebuild-facts')[/dim]")

    conn.close()


if __name__ == "__main__":
    app()
