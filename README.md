# distillgov

> Congress, distilled.

A civic transparency tool that makes congressional activity accessible to everyone. Track your representatives, their votes, and their stock trades — all in plain language.

## Features

- **Your Representatives**: Enter your zip code, see who represents you
- **Voting Records**: How does your rep actually vote? Plain-language summaries
- **Stock Trades**: Congressional stock trading disclosures, made searchable
- **Bill Tracking**: What's Congress working on? Where do bills die?

## Architecture

```
Congress.gov API ─┐
                  ├─▶ Ingestion (Python) ─▶ DuckDB ─▶ FastAPI ─▶ React
CapitolGains ─────┘
```

- **Ingestion**: Python scripts pull from Congress.gov API and congressional disclosure portals
- **Storage**: DuckDB for fast analytics on legislative data
- **API**: FastAPI serves the data
- **Frontend**: React app for the user interface

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- A [Congress.gov API key](https://api.congress.gov/sign-up/) (free)

### Setup

```bash
# Clone the repo
git clone https://github.com/blancas-armando/distillgov.git
cd distillgov

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
playwright install

# Configure environment
cp .env.example .env
# Edit .env and add your CONGRESS_API_KEY

# Initialize database
python -m ingestion.cli init

# Sync data
python -m ingestion.cli sync members
python -m ingestion.cli sync trades --year 2024

# Check stats
python -m ingestion.cli stats
```

### Run the API

```bash
uvicorn api.main:app --reload
```

### Run the Frontend

```bash
cd web
npm install
npm run dev
```

## Data Sources

| Source | Data | Access |
|--------|------|--------|
| [Congress.gov API](https://api.congress.gov/) | Members, bills, votes | Free API key |
| [House Disclosures](https://disclosures-clerk.house.gov/) | Stock trades (House) | Via CapitolGains |
| [Senate Disclosures](https://efdsearch.senate.gov/) | Stock trades (Senate) | Via CapitolGains |

## Project Structure

```
distillgov/
├── ingestion/          # Data sync scripts
│   ├── cli.py          # CLI commands
│   ├── client.py       # Congress.gov API client
│   ├── sync_members.py
│   ├── sync_bills.py
│   ├── sync_votes.py
│   └── sync_trades.py  # Uses CapitolGains
├── api/                # FastAPI backend
├── web/                # React frontend
├── db/
│   └── schema.sql      # DuckDB schema
└── PRODUCT.md          # Product documentation
```

## License

MIT

## Disclaimer

This project is for educational purposes. It is not affiliated with the U.S. Congress or any government agency. Data is sourced from public government websites and APIs.
