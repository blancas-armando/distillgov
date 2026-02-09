"""Distillgov ETL pipeline DAG.

Daily at 6 AM UTC. All tasks run sequentially (DuckDB single-writer).
Incremental by default — sync functions track last run via sync_meta.

Hardened for production:
- execution_timeout per task (prevents runaways)
- on_failure_callback for alerting
- max_active_runs=1 (prevents concurrent pipeline runs)
- quality_check gate after dbt
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

log = logging.getLogger(__name__)

DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt_distillgov"

DAG_DOC = """
### Distillgov Pipeline

Ingests congressional data from Congress.gov and senate.gov, then builds
dbt models on top of DuckDB. **Incremental by default** — only fetches
records updated since the last run.

#### Data flow

```
init_schema → load_zips → [ingest_base] → [ingest_detail] → [enrich] → [dbt] → quality_check
```

| Group | Tasks | Source |
|-------|-------|--------|
| **ingest_base** | members, bills, house_votes, senate_votes | Congress.gov API, senate.gov XML |
| **ingest_detail** | cosponsors, actions, subjects, summaries, house_member_votes, senate_member_votes | Congress.gov API, senate.gov XML |
| **enrich** | enrich_members, committees | YAML files, Congress.gov API |
| **dbt** | run, test | dbt-duckdb |
| **quality_check** | data assertions | DuckDB |

#### Parameters

- **congress** (int): Congress number, default 119
- **session** (int): Session number (1 or 2), default 1

#### Notes

- All tasks run **sequentially** — DuckDB only allows one writer at a time.
- `max_active_runs=1` prevents concurrent pipeline executions.
- Each task has an `execution_timeout` to kill runaways.
- Quality check runs after dbt and fails the pipeline if data looks wrong.
"""


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


def _on_failure(context):
    """Called when any task fails. Logs the error for Airflow UI and alerts."""
    task = context.get("task_instance")
    exception = context.get("exception")
    log.error(
        "PIPELINE FAILURE: task=%s, dag_run=%s, error=%s",
        task.task_id if task else "unknown",
        context.get("dag_run", {}).run_id if context.get("dag_run") else "unknown",
        exception,
    )


# ---------------------------------------------------------------------------
# Default args
# ---------------------------------------------------------------------------

default_args = {
    "owner": "distillgov",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "on_failure_callback": _on_failure,
}

# Timeouts by task type
_TIMEOUT_SHORT = timedelta(minutes=10)     # schema, zips, members, enrichment
_TIMEOUT_MEDIUM = timedelta(minutes=60)    # bills, votes, committees
_TIMEOUT_LONG = timedelta(hours=3)         # detail syncs (cosponsors, actions, subjects, summaries, member-votes)
_TIMEOUT_DBT = timedelta(minutes=30)       # dbt run/test


# ---------------------------------------------------------------------------
# Task callables — lazy imports to avoid import-time DuckDB connections
# ---------------------------------------------------------------------------


def _init_schema(**context):
    import duckdb
    from config import DB_PATH, SCHEMA_PATH

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))
    conn.execute(SCHEMA_PATH.read_text())
    conn.close()


def _load_zips(**context):
    from ingestion.load_zip_districts import load_zip_districts
    load_zip_districts()


def _sync_members(**context):
    from ingestion.sync_members import sync_members
    sync_members(congress=context["params"].get("congress", 119))


def _sync_bills(**context):
    from ingestion.sync_bills import sync_bills
    sync_bills(congress=context["params"].get("congress", 119))


def _sync_votes(**context):
    from ingestion.sync_votes import sync_votes
    sync_votes(congress=context["params"].get("congress", 119))


def _sync_senate_votes(**context):
    from ingestion.sync_votes import sync_senate_votes
    sync_senate_votes(
        congress=context["params"].get("congress", 119),
        session=context["params"].get("session", 1),
    )


def _sync_cosponsors(**context):
    from ingestion.sync_bills import sync_cosponsors
    sync_cosponsors(congress=context["params"].get("congress", 119))


def _sync_actions(**context):
    from ingestion.sync_bills import sync_actions
    sync_actions(congress=context["params"].get("congress", 119))


def _sync_subjects(**context):
    from ingestion.sync_bills import sync_subjects
    sync_subjects(congress=context["params"].get("congress", 119))


def _sync_summaries(**context):
    from ingestion.sync_bills import sync_summaries
    sync_summaries(congress=context["params"].get("congress", 119))


def _sync_member_votes(**context):
    from ingestion.sync_votes import sync_member_votes
    sync_member_votes(congress=context["params"].get("congress", 119))


def _sync_senate_member_votes(**context):
    from ingestion.sync_votes import sync_senate_member_votes
    sync_senate_member_votes(
        congress=context["params"].get("congress", 119),
        session=context["params"].get("session", 1),
    )


def _enrich_members(**context):
    from ingestion.enrich_members import enrich_members
    enrich_members()


def _sync_committees(**context):
    from ingestion.sync_committees import sync_committees
    sync_committees(congress=context["params"].get("congress", 119))


def _dbt_run(**context):
    subprocess.run(
        ["dbt", "run", "--profiles-dir", "."],
        cwd=str(DBT_PROJECT_DIR),
        check=True,
    )


def _dbt_test(**context):
    subprocess.run(
        ["dbt", "test", "--profiles-dir", "."],
        cwd=str(DBT_PROJECT_DIR),
        check=True,
    )


def _quality_check(**context):
    from ingestion.quality import check_and_report

    passed = check_and_report()
    if not passed:
        raise RuntimeError("Data quality checks failed — see logs for details")


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

with DAG(
    dag_id="distillgov_pipeline",
    default_args=default_args,
    description="Ingest congressional data and build dbt models (incremental)",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    params={"congress": 119, "session": 1},
    tags=["distillgov"],
    doc_md=DAG_DOC,
) as dag:

    init_schema = PythonOperator(
        task_id="init_schema",
        python_callable=_init_schema,
        execution_timeout=_TIMEOUT_SHORT,
        doc_md="Create tables if they don't exist (idempotent).",
    )

    load_zips = PythonOperator(
        task_id="load_zips",
        python_callable=_load_zips,
        execution_timeout=_TIMEOUT_SHORT,
        doc_md="Load zip-to-district mappings from CSV.",
    )

    with TaskGroup("ingest_base", tooltip="Core tables from Congress.gov + senate.gov") as ingest_base:
        ingest_members = PythonOperator(
            task_id="members",
            python_callable=_sync_members,
            execution_timeout=_TIMEOUT_SHORT,
            doc_md="Fetch current members of Congress via bioguide.",
        )
        ingest_bills = PythonOperator(
            task_id="bills",
            python_callable=_sync_bills,
            execution_timeout=_TIMEOUT_MEDIUM,
            doc_md="Fetch bills by type. Incremental: only bills updated since last sync.",
        )
        ingest_house_votes = PythonOperator(
            task_id="house_votes",
            python_callable=_sync_votes,
            execution_timeout=_TIMEOUT_MEDIUM,
            doc_md="Fetch House roll call votes. Incremental.",
        )
        ingest_senate_votes = PythonOperator(
            task_id="senate_votes",
            python_callable=_sync_senate_votes,
            execution_timeout=_TIMEOUT_MEDIUM,
            doc_md="Fetch Senate roll call votes from senate.gov XML.",
        )
        ingest_members >> ingest_bills >> ingest_house_votes >> ingest_senate_votes

    with TaskGroup("ingest_detail", tooltip="Detail tables (require base data)") as ingest_detail:
        ingest_cosponsors = PythonOperator(
            task_id="cosponsors",
            python_callable=_sync_cosponsors,
            execution_timeout=_TIMEOUT_LONG,
            doc_md="Fetch bill cosponsors + update sponsor_id. Incremental: only changed bills.",
        )
        ingest_actions = PythonOperator(
            task_id="actions",
            python_callable=_sync_actions,
            execution_timeout=_TIMEOUT_LONG,
            doc_md="Fetch bill action timelines. Incremental: only changed bills.",
        )
        ingest_subjects = PythonOperator(
            task_id="subjects",
            python_callable=_sync_subjects,
            execution_timeout=_TIMEOUT_LONG,
            doc_md="Fetch legislative subject tags. Incremental: only changed bills.",
        )
        ingest_summaries = PythonOperator(
            task_id="summaries",
            python_callable=_sync_summaries,
            execution_timeout=_TIMEOUT_LONG,
            doc_md="Fetch CRS summaries and text URLs. Incremental: only changed bills.",
        )
        ingest_house_member_votes = PythonOperator(
            task_id="house_member_votes",
            python_callable=_sync_member_votes,
            execution_timeout=_TIMEOUT_LONG,
            doc_md="Fetch individual House member voting positions per roll call.",
        )
        ingest_senate_member_votes = PythonOperator(
            task_id="senate_member_votes",
            python_callable=_sync_senate_member_votes,
            execution_timeout=_TIMEOUT_LONG,
            doc_md="Fetch individual Senate member voting positions from senate.gov XML.",
        )
        (
            ingest_cosponsors
            >> ingest_actions
            >> ingest_subjects
            >> ingest_summaries
            >> ingest_house_member_votes
            >> ingest_senate_member_votes
        )

    with TaskGroup("enrich", tooltip="Enrich with external data") as enrich_group:
        enrich_members = PythonOperator(
            task_id="enrich_members",
            python_callable=_enrich_members,
            execution_timeout=_TIMEOUT_SHORT,
            doc_md="Add phone, address, social media from congress-legislators YAML.",
        )
        ingest_committees = PythonOperator(
            task_id="committees",
            python_callable=_sync_committees,
            execution_timeout=_TIMEOUT_MEDIUM,
            doc_md="Fetch committees and membership from Congress.gov.",
        )
        enrich_members >> ingest_committees

    with TaskGroup("dbt", tooltip="Build and test dbt models") as dbt_group:
        dbt_run = PythonOperator(
            task_id="run",
            python_callable=_dbt_run,
            execution_timeout=_TIMEOUT_DBT,
            doc_md="Run all dbt models: staging → intermediate → fact tables → aggregates.",
        )
        dbt_test = PythonOperator(
            task_id="test",
            python_callable=_dbt_test,
            execution_timeout=_TIMEOUT_DBT,
            doc_md="Run dbt tests: unique, not_null, accepted_values on all models.",
        )
        dbt_run >> dbt_test

    quality_check = PythonOperator(
        task_id="quality_check",
        python_callable=_quality_check,
        execution_timeout=_TIMEOUT_SHORT,
        doc_md="Validate data quality: row counts, null checks, regression detection.",
    )

    # Sequential chain — DuckDB single-writer constraint
    init_schema >> load_zips >> ingest_base >> ingest_detail >> enrich_group >> dbt_group >> quality_check
