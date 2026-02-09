select
    bioguide_id,
    full_name,
    party,
    state,
    chamber,
    bills_sponsored,
    bills_enacted,
    bills_passed,
    sponsor_success_rate,
    votes_cast,
    votes_missed,
    attendance_rate,
    party_loyalty_pct,
    activity_score
from {{ ref('fct_members') }}
where is_current = true
order by bills_sponsored desc
