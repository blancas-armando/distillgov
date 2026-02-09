-- Distillgov Fact Tables and Views
-- Run after schema.sql and data sync
-- DuckDB

-- ============================================================================
-- BILL FACTS
-- Enriched bills with computed time dimensions and flags
-- ============================================================================

CREATE OR REPLACE TABLE bill_facts AS
SELECT
    -- Keys
    b.bill_id,
    b.congress,
    b.bill_type,
    b.bill_number,

    -- Core fields
    b.title,
    b.introduced_date,
    b.latest_action_date,
    b.latest_action,
    b.status,
    b.sponsor_id,
    b.policy_area,
    b.origin_chamber,

    -- Sponsor info (denormalized for query performance)
    m.full_name AS sponsor_name,
    m.party AS sponsor_party,
    m.state AS sponsor_state,

    -- Time dimensions (political calendar)
    DATE_TRUNC('week', b.introduced_date) AS introduced_week,
    DATE_TRUNC('month', b.introduced_date) AS introduced_month,
    DATE_TRUNC('quarter', b.introduced_date) AS introduced_quarter,
    EXTRACT(YEAR FROM b.introduced_date) AS introduced_year,

    -- Fiscal year (Oct 1 - Sep 30)
    CASE
        WHEN EXTRACT(MONTH FROM b.introduced_date) >= 10
        THEN EXTRACT(YEAR FROM b.introduced_date)::INTEGER + 1
        ELSE EXTRACT(YEAR FROM b.introduced_date)::INTEGER
    END AS fiscal_year,

    -- Congressional session (1 = odd year, 2 = even year)
    CASE
        WHEN EXTRACT(YEAR FROM b.introduced_date)::INTEGER % 2 = 1 THEN 1
        ELSE 2
    END AS session,

    -- Computed metrics
    DATEDIFF('day', b.introduced_date, CURRENT_DATE) AS days_since_introduced,
    DATEDIFF('day', b.introduced_date, b.latest_action_date) AS days_active,

    -- Status flags
    b.status = 'enacted' AS is_enacted,
    b.status IN ('passed_house', 'passed_senate') AS is_passed,
    b.status = 'in_committee' AS is_in_committee,
    b.status = 'introduced' AS is_new,

    -- Staleness flag (no action in 90+ days)
    DATEDIFF('day', b.latest_action_date, CURRENT_DATE) > 90 AS is_stale,

    -- Recently active (action in last 30 days)
    DATEDIFF('day', b.latest_action_date, CURRENT_DATE) <= 30 AS is_recently_active

FROM bills b
LEFT JOIN members m ON b.sponsor_id = m.bioguide_id;


-- ============================================================================
-- MEMBER FACTS
-- Enriched members with computed sponsorship stats
-- ============================================================================

CREATE OR REPLACE TABLE member_facts AS
WITH sponsorship_stats AS (
    SELECT
        sponsor_id,
        COUNT(*) AS bills_sponsored,
        COUNT(*) FILTER (WHERE status = 'enacted') AS bills_enacted,
        COUNT(*) FILTER (WHERE status IN ('passed_house', 'passed_senate', 'enacted')) AS bills_passed
    FROM bills
    WHERE sponsor_id IS NOT NULL
    GROUP BY sponsor_id
)
SELECT
    -- Keys
    m.bioguide_id,

    -- Core fields
    m.first_name,
    m.last_name,
    m.full_name,
    m.party,
    m.state,
    m.district,
    m.chamber,
    m.is_current,
    m.image_url,
    m.leadership_role,
    m.start_date,

    -- Sponsorship stats
    COALESCE(s.bills_sponsored, 0) AS bills_sponsored,
    COALESCE(s.bills_enacted, 0) AS bills_enacted,
    COALESCE(s.bills_passed, 0) AS bills_passed,

    -- Success rate (avoid division by zero)
    CASE
        WHEN COALESCE(s.bills_sponsored, 0) > 0
        THEN ROUND(100.0 * COALESCE(s.bills_enacted, 0) / s.bills_sponsored, 1)
        ELSE 0
    END AS sponsor_success_rate,

    -- Placeholder for future stats (when data available)
    -- Voting stats
    NULL::INTEGER AS total_roll_calls,
    NULL::INTEGER AS votes_missed,
    NULL::DECIMAL AS attendance_rate,
    NULL::DECIMAL AS party_loyalty_rate,

    -- Trading stats
    NULL::INTEGER AS disclosure_count,
    NULL::INTEGER AS total_trades,
    NULL::INTEGER AS estimated_trade_value

FROM members m
LEFT JOIN sponsorship_stats s ON m.bioguide_id = s.sponsor_id;


-- ============================================================================
-- VIEWS - Rollups at query time
-- ============================================================================

-- Congress-level summary
CREATE OR REPLACE VIEW v_congress_summary AS
SELECT
    congress,
    COUNT(*) AS total_bills,
    COUNT(*) FILTER (WHERE is_enacted) AS enacted,
    COUNT(*) FILTER (WHERE is_passed) AS passed,
    COUNT(*) FILTER (WHERE is_in_committee) AS in_committee,
    COUNT(*) FILTER (WHERE is_new) AS introduced_only,
    COUNT(*) FILTER (WHERE is_stale) AS stale,
    COUNT(*) FILTER (WHERE is_recently_active) AS recently_active,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_enacted) / COUNT(*), 2) AS enactment_rate_pct
FROM bill_facts
GROUP BY congress
ORDER BY congress DESC;


-- Monthly activity
CREATE OR REPLACE VIEW v_monthly_activity AS
SELECT
    introduced_month AS month,
    congress,
    COUNT(*) AS bills_introduced,
    COUNT(*) FILTER (WHERE is_enacted) AS bills_enacted,
    COUNT(*) FILTER (WHERE is_passed) AS bills_passed,
    COUNT(*) FILTER (WHERE sponsor_party = 'D') AS dem_sponsored,
    COUNT(*) FILTER (WHERE sponsor_party = 'R') AS rep_sponsored
FROM bill_facts
WHERE introduced_month IS NOT NULL
GROUP BY introduced_month, congress
ORDER BY introduced_month DESC;


-- Quarterly activity
CREATE OR REPLACE VIEW v_quarterly_activity AS
SELECT
    introduced_quarter AS quarter,
    congress,
    COUNT(*) AS bills_introduced,
    COUNT(*) FILTER (WHERE is_enacted) AS bills_enacted,
    COUNT(*) FILTER (WHERE is_passed) AS bills_passed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_enacted) / COUNT(*), 2) AS enactment_rate_pct
FROM bill_facts
WHERE introduced_quarter IS NOT NULL
GROUP BY introduced_quarter, congress
ORDER BY introduced_quarter DESC;


-- Policy area breakdown
CREATE OR REPLACE VIEW v_policy_breakdown AS
SELECT
    COALESCE(policy_area, 'Unclassified') AS policy_area,
    congress,
    COUNT(*) AS total_bills,
    COUNT(*) FILTER (WHERE is_enacted) AS enacted,
    COUNT(*) FILTER (WHERE is_passed) AS passed,
    COUNT(*) FILTER (WHERE is_in_committee) AS in_committee,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_enacted) / COUNT(*), 2) AS enactment_rate_pct
FROM bill_facts
GROUP BY policy_area, congress
ORDER BY total_bills DESC;


-- Chamber comparison
CREATE OR REPLACE VIEW v_chamber_comparison AS
SELECT
    origin_chamber AS chamber,
    congress,
    COUNT(*) AS total_bills,
    COUNT(*) FILTER (WHERE is_enacted) AS enacted,
    COUNT(*) FILTER (WHERE is_passed) AS passed,
    ROUND(AVG(days_since_introduced), 0) AS avg_days_pending,
    ROUND(AVG(days_active) FILTER (WHERE is_enacted), 0) AS avg_days_to_enactment
FROM bill_facts
GROUP BY origin_chamber, congress
ORDER BY congress DESC, chamber;


-- Party comparison
CREATE OR REPLACE VIEW v_party_breakdown AS
SELECT
    sponsor_party AS party,
    congress,
    COUNT(*) AS bills_sponsored,
    COUNT(*) FILTER (WHERE is_enacted) AS enacted,
    COUNT(*) FILTER (WHERE is_passed) AS passed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_enacted) / COUNT(*), 2) AS enactment_rate_pct
FROM bill_facts
WHERE sponsor_party IS NOT NULL
GROUP BY sponsor_party, congress
ORDER BY congress DESC, party;


-- Member scorecard (top sponsors)
CREATE OR REPLACE VIEW v_member_scorecard AS
SELECT
    bioguide_id,
    full_name,
    party,
    state,
    chamber,
    bills_sponsored,
    bills_enacted,
    bills_passed,
    sponsor_success_rate
FROM member_facts
WHERE is_current = TRUE
ORDER BY bills_sponsored DESC;


-- Bill type breakdown
CREATE OR REPLACE VIEW v_bill_type_breakdown AS
SELECT
    bill_type,
    congress,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE is_enacted) AS enacted,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_enacted) / COUNT(*), 2) AS enactment_rate_pct
FROM bill_facts
GROUP BY bill_type, congress
ORDER BY congress DESC, total DESC;


-- Fiscal year summary
CREATE OR REPLACE VIEW v_fiscal_year_summary AS
SELECT
    fiscal_year,
    COUNT(*) AS bills_introduced,
    COUNT(*) FILTER (WHERE is_enacted) AS enacted,
    COUNT(*) FILTER (WHERE is_passed) AS passed,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_enacted) / COUNT(*), 2) AS enactment_rate_pct
FROM bill_facts
WHERE fiscal_year IS NOT NULL
GROUP BY fiscal_year
ORDER BY fiscal_year DESC;
