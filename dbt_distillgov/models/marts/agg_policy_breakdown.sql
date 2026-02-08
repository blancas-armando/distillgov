select
    coalesce(policy_area, 'Unclassified') as policy_area,
    congress,
    count(*) as total_bills,
    count(*) filter (where is_enacted) as enacted,
    count(*) filter (where is_passed) as passed,
    count(*) filter (where is_in_committee) as in_committee,
    round(100.0 * count(*) filter (where is_enacted) / count(*), 2) as enactment_rate_pct
from {{ ref('fct_bills') }}
group by policy_area, congress
order by total_bills desc
