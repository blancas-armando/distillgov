"""HTTP client for senate.gov roll call vote XML feeds."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx
from rich.console import Console

console = Console()

_BASE_URL = "https://www.senate.gov/legislative/LIS/roll_call_votes"


class SenateClient:
    """Client for fetching Senate vote data from senate.gov XML."""

    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "distillgov/0.1 (civic data pipeline)"},
        )

    def get_vote_menu(self, congress: int, session: int) -> ET.Element | None:
        """Fetch the vote menu XML listing all votes for a congress/session.

        URL pattern: /vote_menu_{congress}_{session}.xml
        Returns the root Element, or None on error.
        """
        url = f"{_BASE_URL}/vote_menu_{congress}_{session}.xml"
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return ET.fromstring(response.text)
        except (httpx.HTTPError, ET.ParseError) as e:
            console.print(f"[yellow]Senate vote menu error ({congress}/{session}): {e}[/yellow]")
            return None

    def get_vote_detail(self, congress: int, session: int, vote_number: int) -> ET.Element | None:
        """Fetch detail XML for a single Senate vote.

        URL pattern: /vote{congress}{session}/vote_{congress}_{session}_{number:05d}.xml
        Returns the root Element, or None on error.
        """
        url = (
            f"{_BASE_URL}/vote{congress}{session}"
            f"/vote_{congress}_{session}_{vote_number:05d}.xml"
        )
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return ET.fromstring(response.text)
        except (httpx.HTTPError, ET.ParseError) as e:
            console.print(f"[dim]  Senate vote detail error ({vote_number}): {e}[/dim]")
            return None

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
