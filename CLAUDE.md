# Distillgov

> Congress, distilled.

A civic transparency tool that makes congressional activity accessible to regular people.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"
playwright install

# Set up environment
cp .env.example .env
# Add your CONGRESS_API_KEY from api.congress.gov

# Initialize database
python -m ingestion.cli init

# Sync data
python -m ingestion.cli sync members
python -m ingestion.cli sync trades

# Run API
uvicorn api.main:app --reload

# Run frontend
cd web && npm install && npm run dev
```

## Architecture

```
Congress.gov API ─┐
                  ├─▶ Ingestion (Python) ─▶ DuckDB ─▶ FastAPI ─▶ React
CapitolGains ─────┘
```

## Key Files

| Path | Purpose |
|------|---------|
| `ingestion/client.py` | Congress.gov API client |
| `ingestion/sync_*.py` | Data sync scripts |
| `db/schema.sql` | DuckDB table definitions |
| `api/main.py` | FastAPI application |
| `api/routers/` | API endpoint handlers |
| `web/` | React frontend |

## Data Sources

- **Congress.gov API**: Members, bills, votes (free, 5k req/hr)
- **CapitolGains**: Stock trading disclosures via official government portals

## Conventions

- Python 3.11+, strict typing
- DuckDB for all data storage
- FastAPI with Pydantic models
- React with TypeScript, Tailwind

## Philosophy

Make complex government data simple. No jargon. Surface insights, not data dumps.
