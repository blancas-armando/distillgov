"""Load zip-to-congressional-district mappings from CSV into DuckDB."""

from __future__ import annotations

import duckdb
from rich.console import Console

from config import DB_PATH

console = Console()

_CSV_PATH = DB_PATH.parent / "zccd.csv"


def load_zip_districts():
    """Load zccd.csv into the zip_districts table.

    Source: OpenSourceActivismTech/us-zipcodes-congress
    CSV headers: state_fips, state_abbr, zcta, cd
    """
    if not _CSV_PATH.exists():
        console.print(f"[red]zccd.csv not found at {_CSV_PATH}[/red]")
        return

    console.print("Loading zip-to-district mappings...")

    conn = duckdb.connect(str(DB_PATH))

    # Clear and reload — this is a static reference dataset
    conn.execute("DELETE FROM zip_districts")

    conn.execute(
        """
        INSERT INTO zip_districts (zcta, state, district)
        SELECT zcta, state_abbr, CAST(cd AS INTEGER)
        FROM read_csv_auto(?)
        """,
        [str(_CSV_PATH)],
    )

    count = conn.execute("SELECT COUNT(*) FROM zip_districts").fetchone()[0]
    conn.close()

    console.print(f"[green]Loaded {count:,} zip-district mappings[/green]")
