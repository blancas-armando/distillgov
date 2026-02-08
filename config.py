"""Centralized paths for distillgov."""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).parent
DB_DIR = ROOT_DIR / "db"

DB_PATH = DB_DIR / "distillgov.duckdb"
SCHEMA_PATH = DB_DIR / "schema.sql"
FACTS_PATH = DB_DIR / "facts.sql"
