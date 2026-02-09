"""Sync committee membership from Congress.gov API to DuckDB."""

from __future__ import annotations

import logging

from ingestion.client import CongressClient
from ingestion.db import get_conn

log = logging.getLogger(__name__)


def sync_committees(congress: int = 118):
    """Sync committees and their members from Congress.gov.

    Fetches the committee list, then fetches membership for each committee.
    """
    log.info("Fetching committees for Congress %d...", congress)

    with CongressClient() as client:
        committees: list[dict] = []
        offset = 0

        while True:
            response = client.get_committees(congress=congress, offset=offset)
            batch = response.get("committees", [])

            if not batch:
                break

            committees.extend(batch)
            offset += len(batch)

            if offset >= response.get("pagination", {}).get("count", 0):
                break

        log.info("Found %d committees", len(committees))

        if not committees:
            return

        with get_conn() as conn:
            committees_inserted = 0
            members_inserted = 0

            for committee in committees:
                name = committee.get("name", "")
                chamber = committee.get("chamber", "")
                committee_type = committee.get("committeeTypeCode", "")
                parent = committee.get("parent")
                parent_id = parent.get("systemCode") if parent else None
                url = committee.get("url")

                system_code = committee.get("systemCode", "")
                if not system_code:
                    continue

                conn.execute(
                    """
                    INSERT OR REPLACE INTO committees (
                        committee_id, name, chamber, committee_type, parent_id, url
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [system_code, name, chamber.lower() if chamber else None,
                     committee_type, parent_id, url]
                )
                committees_inserted += 1

                try:
                    chamber_code = chamber.lower() if chamber else "house"
                    detail = client.get_committee(congress, chamber_code, system_code)
                    committee_data = detail.get("committee", {})

                    current_members = committee_data.get("currentMembers", [])
                    if not current_members:
                        current_members = committee_data.get("members", [])

                    for member in current_members:
                        bioguide_id = member.get("bioguideId")
                        if not bioguide_id:
                            continue

                        role = member.get("role") or "Member"

                        conn.execute(
                            """
                            INSERT OR REPLACE INTO committee_members (
                                committee_id, bioguide_id, role
                            ) VALUES (?, ?, ?)
                            """,
                            [system_code, bioguide_id, role]
                        )
                        members_inserted += 1

                except Exception as e:
                    log.debug("  %s: %s", system_code, e)
                    continue

            log.info("Inserted %d committees, %d memberships", committees_inserted, members_inserted)
