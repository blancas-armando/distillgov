-- Distillgov Database Schema
-- DuckDB

-- Members of Congress (House + Senate)
CREATE TABLE IF NOT EXISTS members (
    bioguide_id     TEXT PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    full_name       TEXT,
    party           TEXT,              -- 'D', 'R', 'I'
    state           TEXT,
    district        INTEGER,           -- NULL for senators
    chamber         TEXT,              -- 'house', 'senate'
    is_current      BOOLEAN DEFAULT TRUE,
    image_url       TEXT,
    official_url    TEXT,
    phone           TEXT,
    office_address  TEXT,
    leadership_role TEXT,
    start_date      DATE,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bills and resolutions
CREATE TABLE IF NOT EXISTS bills (
    bill_id         TEXT PRIMARY KEY,  -- '118-hr-1234'
    congress        INTEGER NOT NULL,
    bill_type       TEXT NOT NULL,     -- 'hr', 's', 'hjres', 'sjres', 'hconres', 'sconres', 'hres', 'sres'
    bill_number     INTEGER NOT NULL,
    title           TEXT,
    short_title     TEXT,
    introduced_date DATE,
    sponsor_id      TEXT,
    policy_area     TEXT,
    origin_chamber  TEXT,
    latest_action   TEXT,
    latest_action_date DATE,
    status          TEXT,              -- 'introduced', 'in_committee', 'passed_house', 'passed_senate', 'enacted', 'vetoed'
    summary         TEXT,
    full_text_url   TEXT,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roll call votes
CREATE TABLE IF NOT EXISTS votes (
    vote_id         TEXT PRIMARY KEY,  -- '118-house-123'
    congress        INTEGER NOT NULL,
    chamber         TEXT NOT NULL,
    session         INTEGER,
    roll_call       INTEGER NOT NULL,
    vote_date       DATE,
    vote_time       TIME,
    question        TEXT,
    description     TEXT,
    result          TEXT,              -- 'Passed', 'Failed', 'Agreed to'
    bill_id         TEXT,
    yea_count       INTEGER,
    nay_count       INTEGER,
    present_count   INTEGER,
    not_voting      INTEGER,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- How each member voted on each roll call
CREATE TABLE IF NOT EXISTS member_votes (
    vote_id         TEXT NOT NULL,
    bioguide_id     TEXT NOT NULL,
    position        TEXT NOT NULL,     -- 'Yes', 'No', 'Present', 'Not Voting'
    PRIMARY KEY (vote_id, bioguide_id)
);

-- Stock trades by members
CREATE TABLE IF NOT EXISTS trades (
    trade_id        TEXT PRIMARY KEY,
    bioguide_id     TEXT NOT NULL,
    transaction_date DATE,
    disclosure_date DATE,
    ticker          TEXT,
    asset_name      TEXT,
    asset_type      TEXT,              -- 'Stock', 'Bond', 'Option', etc.
    trade_type      TEXT NOT NULL,     -- 'Purchase', 'Sale', 'Exchange'
    amount_low      INTEGER,           -- Lower bound of reported range
    amount_high     INTEGER,           -- Upper bound of reported range
    owner           TEXT,              -- 'Self', 'Spouse', 'Child', 'Joint'
    ptr_link        TEXT,              -- Link to original filing
    comment         TEXT,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bill cosponsors
CREATE TABLE IF NOT EXISTS bill_cosponsors (
    bill_id         TEXT NOT NULL,
    bioguide_id     TEXT NOT NULL,
    cosponsor_date  DATE,
    is_original     BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (bill_id, bioguide_id)
);

-- Bill actions timeline
CREATE TABLE IF NOT EXISTS bill_actions (
    bill_id         TEXT NOT NULL,
    action_date     DATE,
    action_text     TEXT,
    action_type     TEXT,
    chamber         TEXT,
    sequence        INTEGER,
    PRIMARY KEY (bill_id, sequence)
);

-- Committees
CREATE TABLE IF NOT EXISTS committees (
    committee_id    TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    chamber         TEXT,
    committee_type  TEXT,              -- 'standing', 'select', 'joint', 'subcommittee'
    parent_id       TEXT,
    url             TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_members_state ON members(state);
CREATE INDEX IF NOT EXISTS idx_members_chamber ON members(chamber);
CREATE INDEX IF NOT EXISTS idx_members_party ON members(party);
CREATE INDEX IF NOT EXISTS idx_members_current ON members(is_current);

CREATE INDEX IF NOT EXISTS idx_bills_congress ON bills(congress);
CREATE INDEX IF NOT EXISTS idx_bills_sponsor ON bills(sponsor_id);
CREATE INDEX IF NOT EXISTS idx_bills_status ON bills(status);
CREATE INDEX IF NOT EXISTS idx_bills_policy_area ON bills(policy_area);

CREATE INDEX IF NOT EXISTS idx_votes_date ON votes(vote_date);
CREATE INDEX IF NOT EXISTS idx_votes_chamber ON votes(chamber);
CREATE INDEX IF NOT EXISTS idx_votes_bill ON votes(bill_id);

CREATE INDEX IF NOT EXISTS idx_member_votes_member ON member_votes(bioguide_id);

CREATE INDEX IF NOT EXISTS idx_trades_member ON trades(bioguide_id);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(transaction_date);
