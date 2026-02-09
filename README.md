# distillgov

> Congress, distilled.

A civic transparency tool that makes congressional activity accessible to everyone. Track your representatives, their votes, committees, and legislation — all in plain language.

## Architecture

```
Congress.gov API ─┐
senate.gov XML ───┼─▶ Ingestion (Python) ─▶ DuckDB ─▶ dbt ─▶ FastAPI ─▶ React
Static CSVs ──────┘
```

- **Ingestion**: Python scripts pull from Congress.gov API, senate.gov XML, and static CSVs
- **Storage**: DuckDB for fast analytics on legislative data
- **dbt**: Staging → intermediate → mart models for enriched facts and aggregations
- **API**: FastAPI serves 24 endpoints
- **Frontend**: React + TypeScript + Tailwind

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- A [Congress.gov API key](https://api.congress.gov/sign-up/) (free)

### Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your CONGRESS_API_KEY

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

# Run dbt models
cd dbt_distillgov && dbt run

# Run API
uvicorn api.main:app --reload

# Run frontend
cd web && npm install && npm run dev
```

## Data Sources

| Source | Data | Access |
|--------|------|--------|
| [Congress.gov API](https://api.congress.gov/) | Members, bills, cosponsors, actions, subjects, summaries, House votes, committees | Free API key (5k req/hr) |
| [senate.gov XML](https://www.senate.gov/legislative/votes.htm) | Senate roll call votes and member positions | Public XML feeds |
| [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) | lis_id → bioguide_id mapping, contact info, social media | Public YAML |
| [unitedstates/images](https://github.com/unitedstates/images) | Deterministic member photo URLs | Public |
| [us-zipcodes-congress](https://github.com/OpenSourceActivismTech/us-zipcodes-congress) | Zip-to-congressional-district mapping | Static CSV |

## Current Data Status

Run `python -m ingestion.cli stats` to check row counts.

| Table | Source | Sync Command | Status |
|-------|--------|--------------|--------|
| `members` | Congress.gov + YAML | `sync members` + `sync enrich-members` | Working (photos, contact, social media) |
| `bills` | Congress.gov | `sync bills` | Working (policy_area, summaries, full text URLs) |
| `bill_cosponsors` | Congress.gov | `sync cosponsors` | Working (also sets sponsor_id) |
| `bill_actions` | Congress.gov | `sync actions` | Working |
| `bill_subjects` | Congress.gov | `sync subjects` | Working (legislative subject tags) |
| `votes` | Congress.gov + senate.gov | `sync votes` + `sync senate-votes` | Working (House + Senate) |
| `member_votes` | Congress.gov + senate.gov | `sync member-votes` + `sync senate-member-votes` | Working (House + Senate positions) |
| `committees` | Congress.gov | `sync committees` | Working (with membership) |
| `committee_members` | Congress.gov | `sync committees` | Working (roles: Chair, Member, etc.) |
| `zip_districts` | Static CSV | `sync load-zips` | Working (~42K mappings) |
| `trades` | House/Senate disclosures | `sync trades` | Via CapitolGains |

## API Endpoints

### Activity

| Endpoint | Description |
|----------|-------------|
| `GET /api/activity/recent` | Unified feed: votes, introductions, enactments (filter by subject, zip, member, chamber) |
| `GET /api/activity/trending-subjects` | Subjects ranked by recent activity |

### Members

| Endpoint | Description |
|----------|-------------|
| `GET /api/members` | List members (filter by chamber, party, state) |
| `GET /api/members/by-zip/{zip}` | Find reps + senators for a zip code |
| `GET /api/members/compare?ids=A,B` | Side-by-side comparison with voting agreement |
| `GET /api/members/{id}` | Full detail: stats, contact, social, committees, recent activity |
| `GET /api/members/{id}/votes` | Voting record (filter by subject, policy_area, passage_only) |
| `GET /api/members/{id}/bills` | Bills sponsored or cosponsored |

### Bills

| Endpoint | Description |
|----------|-------------|
| `GET /api/bills` | List bills (search `q=`, filter by subject, policy, status, sponsor, chamber) |
| `GET /api/bills/categories` | Policy area taxonomy with counts |
| `GET /api/bills/subjects` | Browse legislative subject tags with counts (search with `q=`) |
| `GET /api/bills/{id}` | Detail: summary, full text URL, subjects, cosponsorship breakdown |
| `GET /api/bills/{id}/actions` | Action timeline (intro → committee → vote → signed) |
| `GET /api/bills/{id}/votes` | Roll call votes on a bill |

### Committees

| Endpoint | Description |
|----------|-------------|
| `GET /api/committees` | List committees (search `q=`, filter by chamber) with member counts |
| `GET /api/committees/{id}` | Committee detail with full member list and roles |

### Votes

| Endpoint | Description |
|----------|-------------|
| `GET /api/votes` | List votes (filter by chamber, bill, result, passage_only) |
| `GET /api/votes/{id}` | Vote detail with counts |
| `GET /api/votes/{id}/positions` | Member positions + party breakdown |

### Stats (dbt aggregations)

| Endpoint | Description |
|----------|-------------|
| `GET /api/stats/congress-summary` | Per-congress bill aggregations |
| `GET /api/stats/policy-breakdown` | Bills by policy area |
| `GET /api/stats/chamber-comparison` | House vs Senate |
| `GET /api/stats/party-breakdown` | D vs R sponsorship |
| `GET /api/stats/member-scorecard` | Current member rankings |

## Project Structure

```
distillgov/
├── ingestion/                  # Data sync scripts
│   ├── cli.py                  # CLI commands (sync, init, stats)
│   ├── client.py               # Congress.gov API client
│   ├── senate_client.py        # senate.gov XML client
│   ├── sync_members.py         # Member sync
│   ├── sync_bills.py           # Bills, cosponsors, actions, subjects, summaries
│   ├── sync_votes.py           # House + Senate votes and positions
│   ├── sync_committees.py      # Committees + membership
│   ├── sync_trades.py          # Stock trade disclosures
│   ├── enrich_members.py       # Contact + social media from YAML
│   ├── load_zip_districts.py   # Zip-to-district CSV loader
│   └── constants.py            # Shared state codes, normalization
├── api/                        # FastAPI backend
│   ├── main.py                 # Application entry point
│   └── routers/                # Endpoint handlers
│       ├── activity.py         # Activity feed
│       ├── members.py          # Members
│       ├── bills.py            # Bills
│       ├── votes.py            # Votes
│       ├── committees.py       # Committees
│       └── stats.py            # dbt aggregations
├── db/
│   ├── schema.sql              # DuckDB table definitions
│   └── SCHEMA.md               # Schema documentation with ERD
├── dbt_distillgov/             # dbt models
│   └── models/
│       ├── staging/            # stg_* (clean raw tables)
│       ├── intermediate/       # int_* (shared logic)
│       └── marts/              # fct_* (facts) + agg_* (aggregations)
├── web/                        # React frontend
└── pyproject.toml
```

## Git Workflow

Trunk-based development with conventional commits. Branch protection on `main` — all changes go through PRs.

```
main ← feat/thing ← work happens here
     ← fix/bug
     ← refactor/cleanup
     ← docs/update
```

Commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

## License

MIT

## Disclaimer

This project is for educational purposes. It is not affiliated with the U.S. Congress or any government agency. Data is sourced from public government websites and APIs.
