"""Congress.gov API client with rate limiting and retry."""

from __future__ import annotations

import os
import time
import threading
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.congress.gov/v3"

# Congress.gov limit: 5,000 requests/hour → ~1.4/sec. We use 1/sec for safety.
_RATE_LIMIT_RPS = 1.0
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # seconds: 2, 4, 8
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class _RateLimiter:
    """Simple token-bucket rate limiter (thread-safe)."""

    def __init__(self, rps: float):
        self._min_interval = 1.0 / rps
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()


class CongressClient:
    """Client for the Congress.gov API.

    Features:
    - Rate limiting (~1 req/sec, well under 5k/hr)
    - Retry with exponential backoff on 429/5xx
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CONGRESS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "CONGRESS_API_KEY required. Get one at https://api.congress.gov/sign-up/"
            )
        self.client = httpx.Client(timeout=30.0)
        self._limiter = _RateLimiter(_RATE_LIMIT_RPS)

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request with rate limiting and retry."""
        params = params or {}
        params["api_key"] = self.api_key
        params["format"] = "json"

        url = f"{BASE_URL}/{endpoint}"

        for attempt in range(_MAX_RETRIES + 1):
            self._limiter.wait()
            response = self.client.get(url, params=params)

            if response.status_code not in _RETRYABLE_STATUS:
                response.raise_for_status()
                return response.json()

            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_BASE ** (attempt + 1)
                if response.status_code == 429:
                    # Respect Retry-After header if present
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait = max(wait, int(retry_after))
                time.sleep(wait)

        # Final attempt failed
        response.raise_for_status()
        return response.json()  # unreachable, raise_for_status throws

    def get_members(
        self,
        current_member: bool = True,
        limit: int = 250,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get members of Congress."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if current_member:
            params["currentMember"] = "true"
        return self._get("member", params)

    def get_member(self, bioguide_id: str) -> dict[str, Any]:
        """Get a single member by bioguide ID."""
        return self._get(f"member/{bioguide_id}")

    def get_bills(
        self,
        congress: int,
        bill_type: str | None = None,
        limit: int = 250,
        offset: int = 0,
        from_datetime: str | None = None,
        to_datetime: str | None = None,
    ) -> dict[str, Any]:
        """Get bills for a congress.

        Args:
            from_datetime: ISO format "YYYY-MM-DDT00:00:00Z" — only bills updated after this
            to_datetime: ISO format — only bills updated before this
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if from_datetime:
            params["fromDateTime"] = from_datetime
        if to_datetime:
            params["toDateTime"] = to_datetime

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

    def get_bill_subjects(
        self, congress: int, bill_type: str, bill_number: int
    ) -> dict[str, Any]:
        """Get legislative subjects for a bill."""
        return self._get(f"bill/{congress}/{bill_type}/{bill_number}/subjects")

    def get_bill_summaries(
        self, congress: int, bill_type: str, bill_number: int
    ) -> dict[str, Any]:
        """Get CRS summaries for a bill."""
        return self._get(f"bill/{congress}/{bill_type}/{bill_number}/summaries")

    def get_bill_text(
        self, congress: int, bill_type: str, bill_number: int
    ) -> dict[str, Any]:
        """Get text versions for a bill."""
        return self._get(f"bill/{congress}/{bill_type}/{bill_number}/text")

    def get_committees(
        self, congress: int, chamber: str | None = None, limit: int = 250, offset: int = 0
    ) -> dict[str, Any]:
        """Get committees for a congress."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if chamber:
            return self._get(f"committee/{congress}/{chamber}", params)
        return self._get(f"committee/{congress}", params)

    def get_committee(
        self, congress: int, chamber: str, committee_code: str
    ) -> dict[str, Any]:
        """Get a single committee with details."""
        return self._get(f"committee/{congress}/{chamber}/{committee_code}")

    def get_votes(
        self,
        congress: int,
        chamber: str,
        session: int | None = None,
        limit: int = 250,
        offset: int = 0,
        from_datetime: str | None = None,
        to_datetime: str | None = None,
    ) -> dict[str, Any]:
        """Get roll call votes.

        Args:
            from_datetime: ISO format — only votes updated after this
            to_datetime: ISO format — only votes updated before this
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if from_datetime:
            params["fromDateTime"] = from_datetime
        if to_datetime:
            params["toDateTime"] = to_datetime
        if session:
            endpoint = f"house-vote/{congress}/{session}"
        else:
            endpoint = f"house-vote/{congress}"
        return self._get(endpoint, params)

    def get_vote_members(
        self,
        congress: int,
        session: int,
        roll_call: int,
    ) -> dict[str, Any]:
        """Get individual member voting positions for a roll call vote."""
        endpoint = f"house-vote/{congress}/{session}/{roll_call}/members"
        return self._get(endpoint)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
