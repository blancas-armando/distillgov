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
    target: str = typer.Argument(
        ...,
        help="What to sync: members, bills, cosponsors, actions, subjects, summaries, "
        "votes, member-votes, senate-votes, senate-member-votes, committees, "
        "enrich-members, load-zips, all",
    ),
    congress: int = typer.Option(118, help="Congress number (e.g., 118 for 118th Congress)"),
    from_congress: int | None = typer.Option(None, help="Sync a range: from this congress up to --congress"),
    session: int = typer.Option(1, help="Session number (1 or 2)"),
):
    """Sync data from sources into DuckDB.

    Targets:
      members              - Members of Congress
      bills                - Bills and resolutions
      cosponsors           - Bill cosponsors + sponsor IDs (requires bills)
      actions              - Bill action timelines (requires bills)
      subjects             - Legislative subject tags (requires bills)
      summaries            - CRS bill summaries + text URLs (requires bills)
      votes                - House roll call votes
      member-votes         - House member voting positions (requires votes)
      senate-votes         - Senate roll call votes from senate.gov
      senate-member-votes  - Senate member voting positions (requires senate-votes)
      committees           - Committee membership from Congress.gov
      enrich-members       - Phone, address, social media from YAML
      load-zips            - Load zip-to-district mappings
      all                  - Full pipeline (all of the above)

    Use --from-congress to backfill multiple congresses:
      sync bills --from-congress 117 --congress 118
    """
    congresses = list(range(from_congress, congress + 1)) if from_congress else [congress]

    if target == "all":
        targets = [
            "members", "enrich-members", "bills", "cosponsors", "actions",
            "subjects", "summaries", "votes", "member-votes",
            "senate-votes", "senate-member-votes", "committees", "load-zips",
        ]
    else:
        targets = [target]

    for c in congresses:
        if len(congresses) > 1:
            console.print(f"\n[bold magenta]── Congress {c} ──[/bold magenta]")

        for t in targets:
            console.print(f"\n[bold blue]Syncing {t} (congress={c})...[/bold blue]")

            if t == "members":
                from ingestion.sync_members import sync_members
                sync_members(congress=c)

            elif t == "bills":
                from ingestion.sync_bills import sync_bills
                sync_bills(congress=c)

            elif t == "cosponsors":
                from ingestion.sync_bills import sync_cosponsors
                sync_cosponsors(congress=c)

            elif t == "actions":
                from ingestion.sync_bills import sync_actions
                sync_actions(congress=c)

            elif t == "votes":
                from ingestion.sync_votes import sync_votes
                sync_votes(congress=c)

            elif t == "member-votes":
                from ingestion.sync_votes import sync_member_votes
                sync_member_votes(congress=c)

            elif t == "senate-votes":
                from ingestion.sync_votes import sync_senate_votes
                sync_senate_votes(congress=c, session=session)

            elif t == "senate-member-votes":
                from ingestion.sync_votes import sync_senate_member_votes
                sync_senate_member_votes(congress=c, session=session)

            elif t == "subjects":
                from ingestion.sync_bills import sync_subjects
                sync_subjects(congress=c)

            elif t == "summaries":
                from ingestion.sync_bills import sync_summaries
                sync_summaries(congress=c)

            elif t == "committees":
                from ingestion.sync_committees import sync_committees
                sync_committees(congress=c)

            elif t == "enrich-members":
                from ingestion.enrich_members import enrich_members
                enrich_members()

            elif t == "load-zips":
                from ingestion.load_zip_districts import load_zip_districts
                load_zip_districts()

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
    base_tables = [
        "members", "bills", "bill_cosponsors", "bill_actions",
        "bill_subjects", "votes", "member_votes",
        "committees", "committee_members", "zip_districts",
    ]
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
