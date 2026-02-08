select
    origin_chamber as chamber,
    congress,
    count(*) as total_bills,
    count(*) filter (where is_enacted) as enacted,
    count(*) filter (where is_passed) as passed,
    round(avg(days_since_introduced), 0) as avg_days_pending,
    round(avg(days_active) filter (where is_enacted), 0) as avg_days_to_enactment
from {{ ref('fct_bills') }}
group by origin_chamber, congress
order by congress desc, chamber
