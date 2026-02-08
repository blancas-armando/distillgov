"""Congress.gov API client."""

import os
import httpx
from typing import Any
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.congress.gov/v3"


class CongressClient:
    """Client for the Congress.gov API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "CONGRESS_API_KEY required. Get one at https://api.congress.gov/sign-up/"
            )
        self.client = httpx.Client(timeout=30.0)

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to the API."""
        params = params or {}
        params["api_key"] = self.api_key
        params["format"] = "json"

        url = f"{BASE_URL}/{endpoint}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_members(
        self,
        congress: int | None = None,
        chamber: str | None = None,
        limit: int = 250,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get members of Congress."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if congress and chamber:
            endpoint = f"member/congress/{congress}/{chamber}"
        elif congress:
            endpoint = f"member/congress/{congress}"
        else:
            endpoint = "member"

        return self._get(endpoint, params)

    def get_member(self, bioguide_id: str) -> dict[str, Any]:
        """Get a single member by bioguide ID."""
        return self._get(f"member/{bioguide_id}")

    def get_bills(
        self,
        congress: int,
        bill_type: str | None = None,
        limit: int = 250,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get bills for a congress."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if bill_type:
            endpoint = f"bill/{congress}/{bill_type}"
        else:
            endpoint = f"bill/{congress}"

        return self._get(endpoint, params)

    def get_bill(self, congress: int, bill_type: str, bill_number: int) -> dict[str, Any]:
        """Get a single bill."""
        return self._get(f"bill/{congress}/{bill_type}/{bill_number}")

    def get_bill_actions(
        self, congress: int, bill_type: str, bill_number: int
    ) -> dict[str, Any]:
        """Get actions for a bill."""
        return self._get(f"bill/{congress}/{bill_type}/{bill_number}/actions")

    def get_bill_cosponsors(
        self, congress: int, bill_type: str, bill_number: int
    ) -> dict[str, Any]:
        """Get cosponsors for a bill."""
        return self._get(f"bill/{congress}/{bill_type}/{bill_number}/cosponsors")

    def get_votes(
        self,
        congress: int,
        chamber: str,
        limit: int = 250,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get roll call votes."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        # Note: House votes endpoint is newer, Senate may differ
        endpoint = f"house-vote/{congress}"
        return self._get(endpoint, params)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
