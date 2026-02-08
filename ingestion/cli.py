"""CLI for distillgov data ingestion."""

import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="Distillgov data ingestion CLI")
console = Console()

DB_PATH = Path(__file__).parent.parent / "db" / "distillgov.duckdb"
SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


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
    target: str = typer.Argument(..., help="What to sync: members, bills, votes, trades, all"),
    congress: int = typer.Option(118, help="Congress number (e.g., 118 for 118th Congress)"),
    year: int = typer.Option(2024, help="Year for trades sync"),
):
    """Sync data from sources into DuckDB."""
    if target == "all":
        targets = ["members", "bills", "votes", "trades"]
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
        elif t == "votes":
            from ingestion.sync_votes import sync_votes
            sync_votes(congress=congress)
        elif t == "trades":
            from ingestion.sync_trades import sync_trades
            sync_trades(year=year)
        else:
            console.print(f"[red]Unknown target: {t}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]Completed {t}[/green]")


@app.command()
def stats():
    """Show database statistics."""
    import duckdb

    if not DB_PATH.exists():
        console.print("[red]Database not found. Run 'distill init' first.[/red]")
        raise typer.Exit(1)

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    tables = ["members", "bills", "votes", "member_votes", "trades"]
    console.print("\n[bold]Database Statistics[/bold]\n")

    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            console.print(f"  {table}: [cyan]{count:,}[/cyan] rows")
        except Exception:
            console.print(f"  {table}: [dim]not found[/dim]")

    conn.close()


if __name__ == "__main__":
    app()
