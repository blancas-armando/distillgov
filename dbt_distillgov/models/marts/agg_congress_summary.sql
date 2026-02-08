select
    congress,
    count(*) as total_bills,
    count(*) filter (where is_enacted) as enacted,
    count(*) filter (where is_passed) as passed,
    count(*) filter (where is_in_committee) as in_committee,
    count(*) filter (where is_new) as introduced_only,
    count(*) filter (where is_stale) as stale,
    count(*) filter (where is_recently_active) as recently_active,
    round(100.0 * count(*) filter (where is_enacted) / count(*), 2) as enactment_rate_pct
from {{ ref('fct_bills') }}
group by congress
order by congress desc
