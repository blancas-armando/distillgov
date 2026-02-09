"""Post-sync data quality checks.

Catches silent failures: zero-row syncs, null regressions, and
row count drops that indicate a data loss problem.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ingestion.db import get_conn

log = logging.getLogger(__name__)


@dataclass
class CheckResult:
    table: str
    check: str
    passed: bool
    detail: str


# Minimum expected rows per table (for a fully-populated database).
# Zero means "table may legitimately be empty on first run".
_MIN_ROWS = {
    "members": 500,       # ~535 current members
    "bills": 100,         # at least some bills exist
    "votes": 50,          # at least some votes exist
    "member_votes": 100,
    "bill_cosponsors": 50,
    "bill_actions": 50,
    "bill_subjects": 50,
    "committees": 10,
    "committee_members": 10,
    "zip_districts": 40000,
}

# Columns that should never be all-null in these tables
_NOT_ALL_NULL = {
    "members": ["party", "state", "chamber"],
    "bills": ["title", "status"],
    "votes": ["vote_date", "chamber"],
}


def run_all_checks() -> list[CheckResult]:
    """Run all quality checks and return results.

    Raises no exceptions — collects all results so the caller can decide
    whether to fail the pipeline.
    """
    results: list[CheckResult] = []
    results.extend(_check_row_counts())
    results.extend(_check_null_columns())
    results.extend(_check_row_count_regression())
    return results


def check_and_report() -> bool:
    """Run checks, log results, return True if all passed."""
    results = run_all_checks()

    failures = [r for r in results if not r.passed]
    passes = [r for r in results if r.passed]

    log.info("Quality checks: %d passed, %d failed", len(passes), len(failures))

    for r in failures:
        log.warning("FAIL %s.%s: %s", r.table, r.check, r.detail)

    for r in passes:
        log.debug("PASS %s.%s: %s", r.table, r.check, r.detail)

    return len(failures) == 0


def _check_row_counts() -> list[CheckResult]:
    """Verify each table has at least the minimum expected rows."""
    results = []
    with get_conn(read_only=True) as conn:
        for table, min_rows in _MIN_ROWS.items():
            try:
                count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                passed = count >= min_rows
                results.append(CheckResult(
                    table=table,
                    check="min_rows",
                    passed=passed,
                    detail=f"{count:,} rows (min: {min_rows:,})",
                ))
            except Exception as e:
                results.append(CheckResult(
                    table=table,
                    check="min_rows",
                    passed=False,
                    detail=f"Table missing or error: {e}",
                ))
    return results


def _check_null_columns() -> list[CheckResult]:
    """Verify critical columns are not entirely null."""
    results = []
    with get_conn(read_only=True) as conn:
        for table, columns in _NOT_ALL_NULL.items():
            for col in columns:
                try:
                    row = conn.execute(
                        f"SELECT count(*) FROM {table} WHERE {col} IS NOT NULL"
                    ).fetchone()
                    non_null = row[0]
                    passed = non_null > 0
                    results.append(CheckResult(
                        table=table,
                        check=f"not_all_null:{col}",
                        passed=passed,
                        detail=f"{non_null:,} non-null values",
                    ))
                except Exception as e:
                    results.append(CheckResult(
                        table=table,
                        check=f"not_all_null:{col}",
                        passed=False,
                        detail=f"Error: {e}",
                    ))
    return results


def _check_row_count_regression() -> list[CheckResult]:
    """Compare current row counts against sync_meta to detect data loss.

    If a sync reported N records but the table now has far fewer, something
    went wrong (e.g., a bad migration dropped data).
    """
    results = []
    with get_conn(read_only=True) as conn:
        try:
            meta_rows = conn.execute(
                "SELECT entity, record_count FROM sync_meta WHERE record_count > 0"
            ).fetchall()
        except Exception:
            return results

        entity_to_table = {
            "members": "members",
            "bills": "bills",
            "votes": "votes",
        }

        for entity, last_count in meta_rows:
            # Extract base table name from entity like "bills-118"
            base = entity.split("-")[0] if "-" in entity else entity
            table = entity_to_table.get(base)
            if not table:
                continue

            try:
                current = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                # Flag if current count dropped to less than 50% of last sync
                if last_count > 0 and current < last_count * 0.5:
                    results.append(CheckResult(
                        table=table,
                        check="regression",
                        passed=False,
                        detail=f"Current {current:,} < 50% of last sync ({last_count:,})",
                    ))
                else:
                    results.append(CheckResult(
                        table=table,
                        check="regression",
                        passed=True,
                        detail=f"Current {current:,}, last sync {last_count:,}",
                    ))
            except Exception:
                continue

    return results
