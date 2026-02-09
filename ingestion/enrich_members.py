"""Enrich members with contact info and social media from unitedstates/congress-legislators."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ingestion.db import get_conn

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "db"
_LEGISLATORS_YAML = _DATA_DIR / "legislators-current.yaml"
_SOCIAL_YAML = _DATA_DIR / "legislators-social-media.yaml"

_YAML_BASE = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main"


def _download_if_missing(path: Path, filename: str) -> bool:
    """Download a YAML file from the unitedstates repo if not cached locally."""
    if path.exists():
        return True

    import httpx

    url = f"{_YAML_BASE}/{filename}"
    log.info("Downloading %s...", filename)

    try:
        response = httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        path.write_bytes(response.content)
        log.info("Downloaded %s (%s bytes)", filename, f"{len(response.content):,}")
        return True
    except Exception as e:
        log.error("Failed to download %s: %s", filename, e)
        return False


def enrich_members():
    """Update members with phone, address, contact form, and social media.

    Downloads YAML files from unitedstates/congress-legislators and
    matches by bioguide_id to update member records.
    """
    log.info("Enriching members with contact and social media data...")

    # Download YAML files if needed
    if not _download_if_missing(_LEGISLATORS_YAML, "legislators-current.yaml"):
        return
    if not _download_if_missing(_SOCIAL_YAML, "legislators-social-media.yaml"):
        return

    # Parse YAML files
    log.info("Parsing legislators-current.yaml...")
    with open(_LEGISLATORS_YAML) as f:
        legislators = yaml.safe_load(f)

    log.info("Parsing legislators-social-media.yaml...")
    with open(_SOCIAL_YAML) as f:
        social_media = yaml.safe_load(f)

    # Build lookup by bioguide_id
    contact_by_id: dict[str, dict] = {}
    for leg in legislators:
        bioguide = leg.get("id", {}).get("bioguide")
        if not bioguide:
            continue

        # Get contact from latest term
        terms = leg.get("terms", [])
        latest = terms[-1] if terms else {}

        contact_by_id[bioguide] = {
            "phone": latest.get("phone"),
            "office_address": latest.get("address"),
            "contact_form": latest.get("contact_form"),
        }

    social_by_id: dict[str, dict] = {}
    for entry in social_media:
        bioguide = entry.get("id", {}).get("bioguide")
        if not bioguide:
            continue

        social = entry.get("social", {})
        social_by_id[bioguide] = {
            "twitter": social.get("twitter"),
            "facebook": social.get("facebook"),
            "youtube": social.get("youtube") or social.get("youtube_id"),
        }

    log.info("Loaded %d contact records, %d social records", len(contact_by_id), len(social_by_id))

    # Update database
    with get_conn() as conn:
        members = conn.execute("SELECT bioguide_id FROM members WHERE is_current = TRUE").fetchall()

        # Build batch of update parameters
        update_params = []
        for (bioguide_id,) in members:
            contact = contact_by_id.get(bioguide_id, {})
            social = social_by_id.get(bioguide_id, {})

            if not contact and not social:
                continue

            update_params.append([
                contact.get("phone"),
                contact.get("office_address"),
                contact.get("contact_form"),
                social.get("twitter"),
                social.get("facebook"),
                social.get("youtube"),
                bioguide_id,
            ])

        conn.executemany(
            """
            UPDATE members SET
                phone = coalesce(?, phone),
                office_address = coalesce(?, office_address),
                contact_form = coalesce(?, contact_form),
                twitter = coalesce(?, twitter),
                facebook = coalesce(?, facebook),
                youtube = coalesce(?, youtube)
            WHERE bioguide_id = ?
            """,
            update_params,
        )

    log.info("Enriched %d members with contact + social data", len(update_params))
