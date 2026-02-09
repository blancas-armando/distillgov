"""Distillgov ETL pipeline DAG.

Daily at 6 AM UTC. All tasks run sequentially because DuckDB
only allows a single writer at a time.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt_distillgov"

DAG_DOC = """
### Distillgov Pipeline

Ingests congressional data from Congress.gov and senate.gov, then builds
dbt models on top of DuckDB.

#### Data flow

```
init_schema → load_zips → [ingest_base] → [ingest_detail] → [dbt]
```

| Group | Tasks | Source |
|-------|-------|--------|
| **ingest_base** | members, bills, house_votes, senate_votes | Congress.gov API, senate.gov XML |
| **ingest_detail** | cosponsors, actions, house_member_votes, senate_member_votes | Congress.gov API, senate.gov XML |
| **dbt** | run, test | dbt-duckdb |

#### Parameters

- **congress** (int): Congress number, default 118
- **session** (int): Session number (1 or 2), default 1

#### Notes

- All tasks run **sequentially** — DuckDB only allows one writer at a time.
- dbt models: staging views → intermediate views → fact tables → aggregate views.
"""

default_args = {
    "owner": "distillgov",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


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

    sync_members(congress=context["params"].get("congress", 118))


def _sync_bills(**context):
    from ingestion.sync_bills import sync_bills

    sync_bills(congress=context["params"].get("congress", 118))


def _sync_votes(**context):
    from ingestion.sync_votes import sync_votes

    sync_votes(congress=context["params"].get("congress", 118))


def _sync_senate_votes(**context):
    from ingestion.sync_votes import sync_senate_votes

    sync_senate_votes(
        congress=context["params"].get("congress", 118),
        session=context["params"].get("session", 1),
    )


def _sync_cosponsors(**context):
    from ingestion.sync_bills import sync_cosponsors

    sync_cosponsors(congress=context["params"].get("congress", 118))


def _sync_actions(**context):
    from ingestion.sync_bills import sync_actions

    sync_actions(congress=context["params"].get("congress", 118))


def _sync_member_votes(**context):
    from ingestion.sync_votes import sync_member_votes

    sync_member_votes(congress=context["params"].get("congress", 118))


def _sync_senate_member_votes(**context):
    from ingestion.sync_votes import sync_senate_member_votes

    sync_senate_member_votes(
        congress=context["params"].get("congress", 118),
        session=context["params"].get("session", 1),
    )


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


# ---------------------------------------------------------------------------
# DAG
# ---------------------------------------------------------------------------

with DAG(
    dag_id="distillgov_pipeline",
    default_args=default_args,
    description="Ingest congressional data and build dbt models",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    params={"congress": 118, "session": 1},
    tags=["distillgov"],
    doc_md=DAG_DOC,
) as dag:

    init_schema = PythonOperator(
        task_id="init_schema",
        python_callable=_init_schema,
        doc_md="Create tables if they don't exist (idempotent).",
    )

    load_zips = PythonOperator(
        task_id="load_zips",
        python_callable=_load_zips,
        doc_md="Load zip-to-district mappings from CSV.",
    )

    with TaskGroup("ingest_base", tooltip="Core tables from Congress.gov + senate.gov") as ingest_base:
        ingest_members = PythonOperator(
            task_id="members",
            python_callable=_sync_members,
            doc_md="Fetch current members of Congress via bioguide.",
        )
        ingest_bills = PythonOperator(
            task_id="bills",
            python_callable=_sync_bills,
            doc_md="Fetch bills by type (HR, S, HJRES, etc.). Limited to 500 per type.",
        )
        ingest_house_votes = PythonOperator(
            task_id="house_votes",
            python_callable=_sync_votes,
            doc_md="Fetch House roll call votes.",
        )
        ingest_senate_votes = PythonOperator(
            task_id="senate_votes",
            python_callable=_sync_senate_votes,
            doc_md="Fetch Senate roll call votes from senate.gov XML.",
        )
        ingest_members >> ingest_bills >> ingest_house_votes >> ingest_senate_votes

    with TaskGroup("ingest_detail", tooltip="Detail tables (require base data)") as ingest_detail:
        ingest_cosponsors = PythonOperator(
            task_id="cosponsors",
            python_callable=_sync_cosponsors,
            doc_md="Fetch bill cosponsors + update sponsor_id on bills.",
        )
        ingest_actions = PythonOperator(
            task_id="actions",
            python_callable=_sync_actions,
            doc_md="Fetch bill action timelines.",
        )
        ingest_house_member_votes = PythonOperator(
            task_id="house_member_votes",
            python_callable=_sync_member_votes,
            doc_md="Fetch individual House member voting positions per roll call.",
        )
        ingest_senate_member_votes = PythonOperator(
            task_id="senate_member_votes",
            python_callable=_sync_senate_member_votes,
            doc_md="Fetch individual Senate member voting positions from senate.gov XML.",
        )
        ingest_cosponsors >> ingest_actions >> ingest_house_member_votes >> ingest_senate_member_votes

    with TaskGroup("dbt", tooltip="Build and test dbt models") as dbt_group:
        dbt_run = PythonOperator(
            task_id="run",
            python_callable=_dbt_run,
            doc_md="Run all dbt models: staging → intermediate → fact tables → aggregates.",
        )
        dbt_test = PythonOperator(
            task_id="test",
            python_callable=_dbt_test,
            doc_md="Run dbt tests: unique, not_null, accepted_values on all models.",
        )
        dbt_run >> dbt_test

    # Sequential chain — DuckDB single-writer constraint
    init_schema >> load_zips >> ingest_base >> ingest_detail >> dbt_group
