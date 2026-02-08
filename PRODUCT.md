# Distillgov

> Congress, distilled.

---

## Philosophy

**The problem**: Congress affects everyone, but following it feels impossible. Existing tools (Congress.gov, GovTrack) are built for researchers and policy wonks. Regular people bounce off them.

**Our approach**: Distill the complexity. Take raw legislative data and reduce it to what matters.

- **Surface insights, not data dumps** — "Your rep votes with their party 94% of the time" beats a table of 500 votes
- **Plain language, no jargon** — "Passed the House" not "Ordered to be Reported by Voice Vote"
- **Start personal, go broad** — Your zip code → your reps → their votes → the bills
- **Progressive disclosure** — Simple surface, depth available for those who want it
- **Speed as a feature** — Instant answers, no loading spinners

---

## Audience

**Primary**: Regular people who *should* care about government but feel locked out by complexity.

They might ask:
- "Who represents me?"
- "How does my rep actually vote?"
- "What's Congress working on right now?"
- "Is my representative trading stocks?"

They won't ask:
- "What's the cloture threshold?"
- "Show me the markup schedule for HJRES-47"

**Secondary**: Portfolio piece demonstrating full-stack + data engineering + product thinking.

---

## Core Insights to Surface

| Insight | Why it matters |
|---------|----------------|
| "Your rep voted against their party 12 times this session" | Shows independence (or lack of it) |
| "This bill has 47 Republican and 23 Democratic cosponsors" | Reveals bipartisan support |
| "94% of bills die in committee" | Explains why nothing seems to happen |
| "Your rep bought $50k in pharma stocks before a healthcare vote" | Stock trading transparency |
| "Your two senators voted opposite on 15 bills" | Makes representation tangible |

---

## Data Sources

### Congress.gov API (Official)
- **Members**: All representatives and senators
- **Bills**: Full text, status, actions, summaries
- **Votes**: Roll call votes with member-level positions
- **Committees**: Reports, hearings, meetings
- **Rate limit**: 5,000 requests/hour
- **Auth**: Free API key

### Stock Trading (via CapitolGains)
- **House**: Financial disclosures from 1995+
- **Senate**: Financial disclosures from 2012+
- **Data**: Transaction date, ticker, amount range, buy/sell
- **Source**: Primary government portals (efdsearch.senate.gov, disclosures-clerk.house.gov)

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Congress.gov   │────▶│                 │     │             │
│      API        │     │    Ingestion    │────▶│   DuckDB    │
└─────────────────┘     │    (Python)     │     │             │
                        │                 │     └──────┬──────┘
┌─────────────────┐     │  - sync_members │            │
│  House/Senate   │────▶│  - sync_bills   │            │
│  Disclosures    │     │  - sync_votes   │            │
│  (CapitolGains) │     │  - sync_trades  │            │
└─────────────────┘     └─────────────────┘            │
                                                       ▼
                                                ┌─────────────┐
                                                │   FastAPI   │
                                                │             │
                                                └──────┬──────┘
                                                       │
                                                       ▼
                                                ┌─────────────┐
                                                │    React    │
                                                │   (Vite)    │
                                                └─────────────┘
```

### Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Ingestion | Python + httpx + CapitolGains | Clean async ETL, proven scraping |
| Storage | DuckDB | Fast analytics, no server, single file |
| API | FastAPI | Typed, async, auto-docs |
| Frontend | React + Vite | Fast, familiar |
| Styling | Tailwind | Rapid iteration |

---

## Data Model

### members
```sql
bioguide_id     TEXT PRIMARY KEY,
first_name      TEXT NOT NULL,
last_name       TEXT NOT NULL,
party           TEXT,              -- 'D', 'R', 'I'
state           TEXT,
district        INTEGER,           -- NULL for senators
chamber         TEXT,              -- 'house', 'senate'
is_current      BOOLEAN,
image_url       TEXT,
official_url    TEXT,
phone           TEXT,
office_address  TEXT,
leadership_role TEXT,
start_date      DATE,
updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### bills
```sql
bill_id         TEXT PRIMARY KEY,  -- '118-hr-1234'
congress        INTEGER,
bill_type       TEXT,              -- 'hr', 's', 'hjres', etc.
bill_number     INTEGER,
title           TEXT,
short_title     TEXT,
introduced_date DATE,
sponsor_id      TEXT REFERENCES members(bioguide_id),
policy_area     TEXT,
origin_chamber  TEXT,
latest_action   TEXT,
latest_action_date DATE,
status          TEXT,              -- 'introduced', 'in_committee', 'passed_house', etc.
summary         TEXT,
full_text_url   TEXT,
updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### votes
```sql
vote_id         TEXT PRIMARY KEY,  -- '118-house-123'
congress        INTEGER,
chamber         TEXT,
roll_call       INTEGER,
vote_date       DATE,
vote_time       TIME,
question        TEXT,
description     TEXT,
result          TEXT,              -- 'Passed', 'Failed'
bill_id         TEXT REFERENCES bills(bill_id),
yea_count       INTEGER,
nay_count       INTEGER,
present_count   INTEGER,
not_voting      INTEGER,
updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### member_votes
```sql
vote_id         TEXT REFERENCES votes(vote_id),
bioguide_id     TEXT REFERENCES members(bioguide_id),
position        TEXT,              -- 'Yes', 'No', 'Present', 'Not Voting'
PRIMARY KEY (vote_id, bioguide_id)
```

### trades
```sql
trade_id        TEXT PRIMARY KEY,
bioguide_id     TEXT REFERENCES members(bioguide_id),
transaction_date DATE,
disclosure_date DATE,
ticker          TEXT,
asset_name      TEXT,
trade_type      TEXT,              -- 'Purchase', 'Sale'
amount_low      INTEGER,           -- Lower bound of range
amount_high     INTEGER,           -- Upper bound of range
owner           TEXT,              -- 'Self', 'Spouse', 'Child'
ptr_link        TEXT,              -- Link to filing
updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### bill_cosponsors
```sql
bill_id         TEXT REFERENCES bills(bill_id),
bioguide_id     TEXT REFERENCES members(bioguide_id),
cosponsor_date  DATE,
is_original     BOOLEAN,
PRIMARY KEY (bill_id, bioguide_id)
```

---

## API Endpoints

### Members
```
GET /api/members                    List all (paginated, filterable)
GET /api/members/:bioguideId        Single member detail + stats
GET /api/members/:bioguideId/votes  Member's voting record
GET /api/members/:bioguideId/trades Member's stock trades
GET /api/members/by-zip/:zip        Your representatives
```

### Bills
```
GET /api/bills                      List all (paginated, filterable)
GET /api/bills/:billId              Bill detail
GET /api/bills/:billId/votes        Votes on this bill
GET /api/bills/search?q=            Full-text search
```

### Votes
```
GET /api/votes                      Recent votes
GET /api/votes/:voteId              Vote detail with member breakdown
```

### Trades
```
GET /api/trades                     Recent trades
GET /api/trades/by-ticker/:ticker   Trades for a specific stock
```

### Analytics
```
GET /api/stats/member/:id           Computed stats (party loyalty, etc.)
GET /api/stats/overview             Dashboard numbers
```

---

## UI Pages

### Home
- Zip code input (prominent)
- "What happened this week" — significant votes in plain language
- Recent notable trades

### Your Representatives
- Your 3 reps with photos and key stats
- Party loyalty scores
- Recent votes where they disagreed

### Member Detail
- Photo, name, party, state, term info
- Stats: party loyalty, bills sponsored, trades
- Recent votes
- Stock trading activity

### Bills
- List with status badges
- Filters: status, policy area, chamber
- Search

### Bill Detail
- Status timeline visualization
- Plain-language summary
- Sponsors
- Vote breakdown (if voted on)

### Trades Feed
- Recent congressional trades
- Filter by member, ticker, trade type

---

## MVP Scope

### Must have
- [ ] Zip code → your reps lookup
- [ ] Member directory with search/filter
- [ ] Member detail with voting record
- [ ] Member stock trades
- [ ] Bill listing with status
- [ ] Recent votes feed
- [ ] Mobile-responsive

### Should have
- [ ] Party loyalty scores
- [ ] Bill status timeline
- [ ] Trade alerts (notable trades)

### Later
- [ ] "Your reps disagreed on..." feature
- [ ] Compare two members
- [ ] Notifications

---

## Project Structure

```
distillgov/
├── ingestion/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI commands
│   ├── client.py           # Congress.gov API client
│   ├── sync_members.py
│   ├── sync_bills.py
│   ├── sync_votes.py
│   └── sync_trades.py      # Uses CapitolGains
├── api/
│   ├── __init__.py
│   ├── main.py             # FastAPI app
│   ├── database.py         # DuckDB connection
│   └── routers/
│       ├── members.py
│       ├── bills.py
│       ├── votes.py
│       └── trades.py
├── web/                    # React app (Vite)
│   ├── src/
│   ├── package.json
│   └── ...
├── db/
│   ├── schema.sql
│   └── queries/
├── pyproject.toml
├── PRODUCT.md
├── CLAUDE.md
└── .env.example
```

---

## Next Steps

1. [x] Define product direction
2. [x] Choose name (distillgov)
3. [ ] Create project structure
4. [ ] DuckDB schema
5. [ ] Ingestion: members (Congress.gov API)
6. [ ] Ingestion: trades (CapitolGains)
7. [ ] FastAPI endpoints
8. [ ] React frontend
9. [ ] Polish
