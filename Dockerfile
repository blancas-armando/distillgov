FROM apache/airflow:2.10-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow

COPY pyproject.toml .
COPY config.py .
COPY ingestion/ ingestion/
COPY db/ db/
COPY dbt_distillgov/ dbt_distillgov/

RUN pip install --no-cache-dir -e ".[pipeline]"
