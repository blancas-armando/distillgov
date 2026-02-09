"""Enrich members with contact info and social media from unitedstates/congress-legislators."""

from __future__ import annotations

from pathlib import Path

import duckdb
import yaml
from rich.console import Console

from config import DB_PATH

console = Console()

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
    console.print(f"  Downloading {filename}...")

    try:
        response = httpx.get(url, timeout=60.0, follow_redirects=True)
        response.raise_for_status()
        path.write_bytes(response.content)
        console.print(f"  [green]Downloaded {filename} ({len(response.content):,} bytes)[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Failed to download {filename}: {e}[/red]")
        return False


def enrich_members():
    """Update members with phone, address, contact form, and social media.

    Downloads YAML files from unitedstates/congress-legislators and
    matches by bioguide_id to update member records.
    """
    console.print("[blue]Enriching members with contact and social media data...[/blue]")

    # Download YAML files if needed
    if not _download_if_missing(_LEGISLATORS_YAML, "legislators-current.yaml"):
        return
    if not _download_if_missing(_SOCIAL_YAML, "legislators-social-media.yaml"):
        return

    # Parse YAML files
    console.print("  Parsing legislators-current.yaml...")
    with open(_LEGISLATORS_YAML) as f:
        legislators = yaml.safe_load(f)

    console.print("  Parsing legislators-social-media.yaml...")
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

    console.print(f"  Loaded {len(contact_by_id)} contact records, {len(social_by_id)} social records")

    # Update database
    conn = duckdb.connect(str(DB_PATH))
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

    conn.close()
    console.print(f"[green]Enriched {len(update_params)} members with contact + social data[/green]")
