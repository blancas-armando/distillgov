"""Shared constants for distillgov ingestion."""

from __future__ import annotations

# Full state name → 2-letter abbreviation
STATE_CODES: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
    "Puerto Rico": "PR", "Guam": "GU", "American Samoa": "AS",
    "U.S. Virgin Islands": "VI", "Northern Mariana Islands": "MP",
}

# 2-letter abbreviation → full state name
STATE_ABBRS: dict[str, str] = {v: k for k, v in STATE_CODES.items()}

# Set of valid abbreviations for quick membership checks
_VALID_ABBRS = set(STATE_CODES.values())


def normalize_state(state: str | None) -> str | None:
    """Normalize a state name or abbreviation to 2-letter code.

    Accepts "California", "CA", "ca" → "CA".
    Returns None for unrecognized values.
    """
    if not state:
        return None
    if len(state) == 2 and state.upper() in _VALID_ABBRS:
        return state.upper()
    return STATE_CODES.get(state)
