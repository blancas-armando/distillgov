"""Sync bills from Congress.gov API to DuckDB."""

from __future__ import annotations

import logging
import re

from rich.progress import track

from ingestion.client import CongressClient
from ingestion.constants import check_consecutive_errors
from ingestion.db import get_conn
from ingestion.sync_meta import get_last_sync, set_last_sync

log = logging.getLogger(__name__)

BILL_TYPES = ["hr", "s", "hjres", "sjres", "hconres", "sconres", "hres", "sres"]


def sync_bills(
    congress: int = 118,
    bill_types: list[str] | None = None,
    with_details: bool = False,
    full: bool = False,
):
    """Sync bills from a Congress into DuckDB.

    Incremental by default — only fetches bills updated since the last sync.
    """
    bill_types = bill_types or BILL_TYPES

    from_dt = None if full else get_last_sync(f"bills-{congress}")
    mode = "incremental" if from_dt else "full"
    log.info("Fetching bills from Congress %d (%s)", congress, mode)
    if from_dt:
        log.info("  Since: %s", from_dt)

    with CongressClient() as client:
        bills = []

        for bill_type in bill_types:
            log.info("  Fetching %s...", bill_type.upper())
            offset = 0

            while True:
                response = client.get_bills(
                    congress=congress,
                    bill_type=bill_type,
                    offset=offset,
                    from_datetime=from_dt,
                )
                batch = response.get("bills", [])

                if not batch:
                    break

                bills.extend(batch)
                offset += len(batch)

                if offset >= response.get("pagination", {}).get("count", 0):
                    break

        log.info("Fetched %d bills", len(bills))

    with get_conn() as conn:
        inserted = 0
        for bill in track(bills, description="Loading bills..."):
            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number")

            if not bill_number:
                continue

            bill_id = f"{congress}-{bill_type}-{bill_number}"

            latest_action = bill.get("latestAction", {})
            latest_action_text = latest_action.get("text")
            latest_action_date = latest_action.get("actionDate")
            status = determine_status(latest_action_text)
            policy_area = bill.get("policyArea", {}).get("name") if bill.get("policyArea") else None

            conn.execute(
                """
                INSERT OR REPLACE INTO bills (
                    bill_id, congress, bill_type, bill_number,
                    title, introduced_date, origin_chamber,
                    latest_action, latest_action_date, status,
                    policy_area, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                [
                    bill_id, congress, bill_type, bill_number,
                    bill.get("title"), bill.get("introducedDate"),
                    bill.get("originChamber"), latest_action_text,
                    latest_action_date, status, policy_area,
                ],
            )
            inserted += 1

    log.info("Inserted %d bills", inserted)
    set_last_sync(f"bills-{congress}", inserted)

    if with_details:
        sync_bill_details(congress, bills)


def sync_bill_details(congress: int, bills: list[dict]):
    """Sync cosponsors and actions for bills."""
    log.info("Fetching cosponsors and actions for %d bills", len(bills))

    cosponsors_inserted = 0
    actions_inserted = 0
    sponsors_updated = 0

    with get_conn() as conn, CongressClient() as client:
        for bill in track(bills, description="Fetching bill details..."):
            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number")

            if not bill_number:
                continue

            bill_id = f"{congress}-{bill_type}-{bill_number}"

            try:
                detail = client.get_bill(congress, bill_type, bill_number)
                bill_data = detail.get("bill", {})

                sponsors = bill_data.get("sponsors", [])
                if sponsors:
                    sponsor_id = sponsors[0].get("bioguideId")
                    if sponsor_id:
                        conn.execute(
                            "UPDATE bills SET sponsor_id = ? WHERE bill_id = ?",
                            [sponsor_id, bill_id],
                        )
                        sponsors_updated += 1

                cosponsors_response = client.get_bill_cosponsors(congress, bill_type, bill_number)
                for cosponsor in cosponsors_response.get("cosponsors", []):
                    bioguide_id = cosponsor.get("bioguideId")
                    if not bioguide_id:
                        continue
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO bill_cosponsors (
                            bill_id, bioguide_id, cosponsor_date, is_original
                        ) VALUES (?, ?, ?, ?)
                        """,
                        [bill_id, bioguide_id, cosponsor.get("sponsorshipDate"),
                         cosponsor.get("isOriginalCosponsor", False)],
                    )
                    cosponsors_inserted += 1

                actions_response = client.get_bill_actions(congress, bill_type, bill_number)
                for idx, action in enumerate(actions_response.get("actions", [])):
                    action_code = action.get("actionCode", "")
                    if action_code.startswith("H"):
                        chamber = "house"
                    elif action_code.startswith("S"):
                        chamber = "senate"
                    else:
                        chamber = None

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO bill_actions (
                            bill_id, action_date, action_text, action_type, chamber, sequence
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [bill_id, action.get("actionDate"), action.get("text"),
                         action.get("type"), chamber, idx],
                    )
                    actions_inserted += 1

            except Exception as e:
                log.debug("  %s: %s", bill_id, e)
                continue

    log.info("Updated %d sponsors", sponsors_updated)
    log.info("Inserted %d cosponsors", cosponsors_inserted)
    log.info("Inserted %d actions", actions_inserted)


def sync_cosponsors(congress: int = 118, full: bool = False):
    """Sync cosponsors for bills in the database.

    Incremental by default — only processes bills updated since last sync.
    """
    log.info("Syncing cosponsors for Congress %d", congress)

    from_dt = None if full else get_last_sync(f"cosponsors-{congress}")

    with get_conn() as conn:
        if from_dt:
            log.info("  Incremental: only bills updated since %s", from_dt)
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ? AND updated_at >= ?",
                [congress, from_dt],
            ).fetchall()
        else:
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
                [congress],
            ).fetchall()

        if not bills:
            log.warning("No bills found. Run 'sync bills' first.")
            return

        log.info("Found %d bills", len(bills))
        inserted = 0
        sponsors_updated = 0
        consecutive_errors = 0

        with CongressClient() as client:
            for bill_id, bill_type, bill_number in track(bills, description="Fetching cosponsors..."):
                try:
                    detail = client.get_bill(congress, bill_type, bill_number)
                    bill_data = detail.get("bill", {})

                    sponsors = bill_data.get("sponsors", [])
                    if sponsors:
                        sponsor_id = sponsors[0].get("bioguideId")
                        if sponsor_id:
                            conn.execute(
                                "UPDATE bills SET sponsor_id = ? WHERE bill_id = ?",
                                [sponsor_id, bill_id],
                            )
                            sponsors_updated += 1

                    titles = bill_data.get("titles", [])
                    for t in titles:
                        if t.get("titleType", "").startswith("Short Title"):
                            short = t.get("title")
                            if short:
                                conn.execute(
                                    "UPDATE bills SET short_title = ? WHERE bill_id = ?",
                                    [short, bill_id],
                                )
                                break

                    response = client.get_bill_cosponsors(congress, bill_type, bill_number)
                    for cosponsor in response.get("cosponsors", []):
                        bioguide_id = cosponsor.get("bioguideId")
                        if not bioguide_id:
                            continue
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO bill_cosponsors (
                                bill_id, bioguide_id, cosponsor_date, is_original
                            ) VALUES (?, ?, ?, ?)
                            """,
                            [bill_id, bioguide_id, cosponsor.get("sponsorshipDate"),
                             cosponsor.get("isOriginalCosponsor", False)],
                        )
                        inserted += 1

                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    log.debug("  %s: %s", bill_id, e)
                    check_consecutive_errors(consecutive_errors, e)
                    continue

    log.info("Updated %d bill sponsors", sponsors_updated)
    log.info("Inserted %d cosponsors", inserted)
    set_last_sync(f"cosponsors-{congress}", inserted)


def sync_actions(congress: int = 118, full: bool = False):
    """Sync actions for bills in the database.

    Incremental by default — only processes bills updated since last sync.
    """
    log.info("Syncing bill actions for Congress %d", congress)

    from_dt = None if full else get_last_sync(f"actions-{congress}")

    with get_conn() as conn:
        if from_dt:
            log.info("  Incremental: only bills updated since %s", from_dt)
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ? AND updated_at >= ?",
                [congress, from_dt],
            ).fetchall()
        else:
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
                [congress],
            ).fetchall()

        if not bills:
            log.warning("No bills found. Run 'sync bills' first.")
            return

        log.info("Found %d bills", len(bills))
        inserted = 0
        consecutive_errors = 0

        with CongressClient() as client:
            for bill_id, bill_type, bill_number in track(bills, description="Fetching actions..."):
                try:
                    response = client.get_bill_actions(congress, bill_type, bill_number)
                    for idx, action in enumerate(response.get("actions", [])):
                        action_code = action.get("actionCode", "")
                        if action_code.startswith("H"):
                            chamber = "house"
                        elif action_code.startswith("S"):
                            chamber = "senate"
                        else:
                            chamber = None

                        conn.execute(
                            """
                            INSERT OR REPLACE INTO bill_actions (
                                bill_id, action_date, action_text, action_type, chamber, sequence
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            [bill_id, action.get("actionDate"), action.get("text"),
                             action.get("type"), chamber, idx],
                        )
                        inserted += 1

                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    log.debug("  %s: %s", bill_id, e)
                    check_consecutive_errors(consecutive_errors, e)
                    continue

    log.info("Inserted %d actions", inserted)
    set_last_sync(f"actions-{congress}", inserted)


def sync_subjects(congress: int = 118, full: bool = False):
    """Sync legislative subject tags for bills.

    Incremental by default — only processes bills updated since last sync.
    """
    log.info("Syncing bill subjects for Congress %d", congress)

    from_dt = None if full else get_last_sync(f"subjects-{congress}")

    with get_conn() as conn:
        if from_dt:
            log.info("  Incremental: only bills updated since %s", from_dt)
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ? AND updated_at >= ?",
                [congress, from_dt],
            ).fetchall()
        else:
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
                [congress],
            ).fetchall()

        if not bills:
            log.warning("No bills found. Run 'sync bills' first.")
            return

        log.info("Found %d bills", len(bills))
        inserted = 0
        consecutive_errors = 0

        with CongressClient() as client:
            for bill_id, bill_type, bill_number in track(bills, description="Fetching subjects..."):
                try:
                    response = client.get_bill_subjects(congress, bill_type, bill_number)
                    subjects = response.get("subjects", {})

                    for subj in subjects.get("legislativeSubjects", []):
                        name = subj.get("name")
                        if name:
                            conn.execute(
                                "INSERT OR REPLACE INTO bill_subjects (bill_id, subject) VALUES (?, ?)",
                                [bill_id, name],
                            )
                            inserted += 1

                    policy = subjects.get("policyArea", {})
                    if policy and policy.get("name"):
                        conn.execute(
                            "UPDATE bills SET policy_area = ? WHERE bill_id = ? AND policy_area IS NULL",
                            [policy["name"], bill_id],
                        )

                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    log.debug("  %s: %s", bill_id, e)
                    check_consecutive_errors(consecutive_errors, e)
                    continue

    log.info("Inserted %d subject tags", inserted)
    set_last_sync(f"subjects-{congress}", inserted)


def sync_summaries(congress: int = 118, full: bool = False):
    """Sync CRS summaries and text version URLs for bills.

    Incremental by default — only processes bills updated since last sync.
    """
    log.info("Syncing bill summaries for Congress %d", congress)

    from_dt = None if full else get_last_sync(f"summaries-{congress}")

    with get_conn() as conn:
        if from_dt:
            log.info("  Incremental: only bills updated since %s", from_dt)
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ? AND updated_at >= ?",
                [congress, from_dt],
            ).fetchall()
        else:
            bills = conn.execute(
                "SELECT bill_id, bill_type, bill_number FROM bills WHERE congress = ?",
                [congress],
            ).fetchall()

        if not bills:
            log.warning("No bills found. Run 'sync bills' first.")
            return

        log.info("Found %d bills", len(bills))
        summaries_updated = 0
        text_updated = 0
        consecutive_errors = 0

        with CongressClient() as client:
            for bill_id, bill_type, bill_number in track(bills, description="Fetching summaries..."):
                try:
                    sum_response = client.get_bill_summaries(congress, bill_type, bill_number)
                    summaries = sum_response.get("summaries", [])
                    if summaries:
                        latest = summaries[-1]
                        text = latest.get("text", "")
                        if text:
                            clean = re.sub(r"<[^>]+>", "", text).strip()
                            conn.execute(
                                "UPDATE bills SET summary = ? WHERE bill_id = ?",
                                [clean, bill_id],
                            )
                            summaries_updated += 1

                    text_response = client.get_bill_text(congress, bill_type, bill_number)
                    versions = text_response.get("textVersions", [])
                    if versions:
                        latest_text = versions[-1]
                        formats = latest_text.get("formats", [])
                        url = None
                        for fmt in formats:
                            if fmt.get("type") == "Formatted Text (PDF)":
                                url = fmt.get("url")
                                break
                        if not url:
                            for fmt in formats:
                                if fmt.get("url"):
                                    url = fmt.get("url")
                                    break
                        if url:
                            conn.execute(
                                "UPDATE bills SET full_text_url = ? WHERE bill_id = ?",
                                [url, bill_id],
                            )
                            text_updated += 1

                    consecutive_errors = 0
                except Exception as e:
                    consecutive_errors += 1
                    log.debug("  %s: %s", bill_id, e)
                    check_consecutive_errors(consecutive_errors, e)
                    continue

    log.info("Updated %d summaries, %d text URLs", summaries_updated, text_updated)
    set_last_sync(f"summaries-{congress}", summaries_updated + text_updated)


def determine_status(action_text: str | None) -> str:
    """Determine bill status from latest action text."""
    if not action_text:
        return "introduced"

    action_lower = action_text.lower()

    if "became public law" in action_lower or "signed by president" in action_lower:
        return "enacted"
    elif "vetoed" in action_lower:
        return "vetoed"
    elif "passed senate" in action_lower:
        return "passed_senate"
    elif "passed house" in action_lower:
        return "passed_house"
    elif "referred to" in action_lower and "committee" in action_lower:
        return "in_committee"
    else:
        return "introduced"


if __name__ == "__main__":
    sync_bills()
