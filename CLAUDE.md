# Distillgov

> Congress, distilled.

A civic transparency tool that makes congressional activity accessible to regular people.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Add your CONGRESS_API_KEY from api.congress.gov

# Initialize database
python -m ingestion.cli init

# Sync all data (full pipeline)
python -m ingestion.cli sync all

# Or sync individual targets
python -m ingestion.cli sync members
python -m ingestion.cli sync enrich-members  # phone, address, social media
python -m ingestion.cli sync bills
python -m ingestion.cli sync cosponsors      # also sets sponsor_id
python -m ingestion.cli sync actions
python -m ingestion.cli sync subjects        # legislative subject tags
python -m ingestion.cli sync summaries       # CRS summaries + full text URLs
python -m ingestion.cli sync votes
python -m ingestion.cli sync member-votes
python -m ingestion.cli sync senate-votes
python -m ingestion.cli sync senate-member-votes
python -m ingestion.cli sync committees
python -m ingestion.cli sync load-zips

# Backfill multiple congresses
python -m ingestion.cli sync all --from-congress 117 --congress 118

# Run API
uvicorn api.main:app --reload

# Run frontend
cd web && npm install && npm run dev
```

## Architecture

```
Congress.gov API ─┐
senate.gov XML ───┼─▶ Ingestion (Python) ─▶ DuckDB ─▶ dbt ─▶ FastAPI ─▶ React
Static CSVs ──────┘
```

## Key Files

| Path | Purpose |
|------|---------|
| `ingestion/client.py` | Congress.gov API client |
| `ingestion/senate_client.py` | senate.gov XML client |
| `ingestion/sync_*.py` | Data sync scripts |
| `ingestion/sync_committees.py` | Committee membership sync |
| `ingestion/enrich_members.py` | Contact + social media from YAML |
| `ingestion/constants.py` | Shared state codes, normalization |
| `db/schema.sql` | DuckDB table definitions |
| `db/SCHEMA.md` | **Schema documentation with ERD** |
| `dbt_distillgov/` | dbt models: staging → intermediate → marts |
| `api/main.py` | FastAPI application |
| `api/routers/` | API endpoint handlers |
| `web/` | React frontend |

## Database Schema

**IMPORTANT**: See `db/SCHEMA.md` for the full schema documentation including:
- Entity Relationship Diagram (visual)
- All tables with column descriptions
- Relationships between tables

**When modifying the database:**
1. Update `db/schema.sql` with the DDL changes
2. Update `db/SCHEMA.md` to reflect the changes (ERD + table docs)
3. Keep both files in sync

## Data Sources

- **Congress.gov API**: Members, bills, cosponsors, actions, subjects, summaries, House votes, committees (free, 5k req/hr)
- **senate.gov XML**: Senate roll call votes and member positions
- **unitedstates/congress-legislators**: lis_id → bioguide_id mapping, contact info, social media
- **unitedstates/images**: Deterministic member photo URLs
- **OpenSourceActivismTech/us-zipcodes-congress**: Zip-to-congressional-district mapping

## Current Data Status

Run `python -m ingestion.cli stats` to check current row counts.

| Table | Source | Status |
|-------|--------|--------|
| members | Congress.gov + YAML | Working (photos, contact, social media) |
| bills | Congress.gov | Working (policy_area, summaries, full text URLs) |
| bill_cosponsors | Congress.gov | Working (with `sync cosponsors`) |
| bill_actions | Congress.gov | Working (with `sync actions`) |
| bill_subjects | Congress.gov | Working (legislative subject tags) |
| votes | Congress.gov + senate.gov | Working (House + Senate, with bill linkage) |
| member_votes | Congress.gov + senate.gov | Working (House + Senate positions) |
| committees | Congress.gov | Working (with membership) |
| committee_members | Congress.gov | Working (roles: Chair, Member, etc.) |
| zip_districts | Static CSV | Working (~42K mappings) |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/activity/recent` | Unified feed: votes, introductions, enactments (filter by subject, zip, member, chamber) |
| `GET /api/activity/trending-subjects` | Subjects ranked by recent activity |
| `GET /api/members` | List members (filter by chamber, party, state) |
| `GET /api/members/by-zip/{zip}` | Find reps + senators for a zip code |
| `GET /api/members/compare?ids=A,B` | Side-by-side comparison with voting agreement |
| `GET /api/members/{id}` | Full detail: stats, contact, social, committees, recent activity |
| `GET /api/members/{id}/votes` | Voting record (filter by subject, policy_area, passage_only) |
| `GET /api/members/{id}/bills` | Bills sponsored or cosponsored |
| `GET /api/bills` | List bills (search `q=`, filter by subject, policy, status, sponsor, chamber) |
| `GET /api/bills/categories` | Policy area taxonomy with counts |
| `GET /api/bills/subjects` | Browse legislative subject tags with counts (search with `q=`) |
| `GET /api/bills/{id}` | Detail: summary, full text URL, subjects, cosponsorship breakdown |
| `GET /api/bills/{id}/actions` | Action timeline (intro → committee → vote → signed) |
| `GET /api/bills/{id}/votes` | Roll call votes on a bill |
| `GET /api/committees` | List committees (search `q=`, filter by chamber) with member counts |
| `GET /api/committees/{id}` | Committee detail with full member list and roles |
| `GET /api/votes` | List votes (filter by chamber, bill, result, passage_only) |
| `GET /api/votes/{id}` | Vote detail with counts |
| `GET /api/votes/{id}/positions` | Member positions + party breakdown |
| `GET /api/stats/congress-summary` | Per-congress bill aggregations |
| `GET /api/stats/policy-breakdown` | Bills by policy area |
| `GET /api/stats/chamber-comparison` | House vs Senate |
| `GET /api/stats/party-breakdown` | D vs R sponsorship |
| `GET /api/stats/member-scorecard` | Current member rankings |

## Git Workflow

**Trunk-based development with conventional commits. Branch protection is enabled on `main` — all changes go through PRs.**

### Workflow
```bash
# 1. Create feature branch from main
git checkout main
git pull
git checkout -b feat/my-feature

# 2. Make changes, commit with conventional commits
git add <files>
git commit -m "feat: add congress overview aggregation table"

# 3. Push feature branch and open PR
git push -u origin feat/my-feature
gh pr create --title "feat: add congress overview aggregation table" --body "..."

# 4. Merge PR (no direct pushes to main)
gh pr merge --merge
```

### Rules
- **Never push directly to `main`** — branch protection enforces this
- Always merge via pull request
- Delete feature branches after merge

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

- Python 3.11+ with `from __future__ import annotations`
- DuckDB for all data storage
- FastAPI with Pydantic models
- dbt for analytics layer (staging → intermediate → marts)
- React with TypeScript, Tailwind

## Philosophy

Make complex government data simple. No jargon. Surface insights, not data dumps.

The goal is to answer questions like:
- "Who represents me?"
- "How does my rep vote?"
- "What's Congress working on?"

Not questions like:
- "What's the cloture threshold?"
- "Show me HJRES-47 markup schedule"
