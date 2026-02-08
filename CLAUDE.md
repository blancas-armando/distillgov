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
python -m ingestion.cli sync bills
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
| `db/SCHEMA.md` | **Schema documentation with ERD** |
| `api/main.py` | FastAPI application |
| `api/routers/` | API endpoint handlers |
| `web/` | React frontend |

## Database Schema

**IMPORTANT**: See `db/SCHEMA.md` for the full schema documentation including:
- Entity Relationship Diagram (visual)
- All tables with column descriptions
- Relationships between tables
- Planned aggregation tables

**When modifying the database:**
1. Update `db/schema.sql` with the DDL changes
2. Update `db/SCHEMA.md` to reflect the changes (ERD + table docs)
3. Keep both files in sync

## Data Sources

- **Congress.gov API**: Members, bills, votes (free, 5k req/hr)
- **CapitolGains**: Stock trading disclosures via official government portals

## Current Data Status

Run `python -m ingestion.cli stats` to check current row counts.

| Table | Source | Status |
|-------|--------|--------|
| members | Congress.gov | ✓ Working |
| bills | Congress.gov | ✓ Working |
| votes | Congress.gov | Needs endpoint fix |
| trades | CapitolGains | ✓ Working (slow) |
| bill_cosponsors | Congress.gov | Not syncing yet |
| bill_actions | Congress.gov | Not syncing yet |

## Git Workflow

**Trunk-based development with conventional commits.**

### Workflow
```bash
# 1. Create feature branch from main
git checkout main
git pull
git checkout -b feat/my-feature

# 2. Make changes, commit with conventional commits
git add <files>
git commit -m "feat: add congress overview aggregation table"

# 3. Merge back to main
git checkout main
git merge feat/my-feature

# 4. Push
git push
```

### Branch Naming
```
feat/thing      # New feature
fix/bug         # Bug fix
refactor/thing  # Code refactoring
docs/thing      # Documentation
chore/thing     # Maintenance
```

### Commit Messages
Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add member stats aggregation table
fix: correct state code mapping for territories
refactor: simplify bill status determination
docs: update schema ERD with new tables
chore: upgrade dependencies
```

Keep commits small and focused. Each commit should be easy to understand.

## Conventions

- Python 3.9+ with `from __future__ import annotations`
- DuckDB for all data storage
- FastAPI with Pydantic models
- React with TypeScript, Tailwind

## Philosophy

Make complex government data simple. No jargon. Surface insights, not data dumps.

The goal is to answer questions like:
- "Who represents me?"
- "How does my rep vote?"
- "What's Congress working on?"
- "Is my rep trading stocks?"

Not questions like:
- "What's the cloture threshold?"
- "Show me HJRES-47 markup schedule"
