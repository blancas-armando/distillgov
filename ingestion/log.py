"""Structured logging for the ingestion pipeline.

Works in both CLI (rich-formatted) and Airflow (plain) contexts.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Generator


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger for the ingestion package.

    Detects Airflow automatically and uses plain format.
    Uses rich format in CLI when available.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Detect Airflow
    in_airflow = "AIRFLOW_HOME" in os.environ or "airflow" in sys.modules

    root = logging.getLogger("ingestion")
    root.setLevel(log_level)

    if root.handlers:
        return  # Already configured

    if in_airflow:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
        )
    else:
        try:
            from rich.logging import RichHandler

            handler = RichHandler(
                rich_tracebacks=True,
                show_path=False,
                markup=True,
            )
        except ImportError:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
            )

    root.addHandler(handler)


@contextmanager
def log_duration(logger: logging.Logger, task_name: str) -> Generator[None, None, None]:
    """Context manager that logs how long a task takes.

    Usage:
        with log_duration(log, "sync_bills"):
            sync_bills()
        # logs: "sync_bills completed in 45.2s"
    """
    start = time.monotonic()
    logger.info(f"{task_name}: starting")
    try:
        yield
        elapsed = time.monotonic() - start
        logger.info(f"{task_name}: completed in {elapsed:.1f}s")
    except Exception:
        elapsed = time.monotonic() - start
        logger.error(f"{task_name}: failed after {elapsed:.1f}s")
        raise


# Auto-configure on import
setup_logging()
