select
    introduced_quarter as quarter,
    congress,
    count(*) as bills_introduced,
    count(*) filter (where is_enacted) as bills_enacted,
    count(*) filter (where is_passed) as bills_passed,
    round(100.0 * count(*) filter (where is_enacted) / count(*), 2) as enactment_rate_pct
from {{ ref('fct_bills') }}
where introduced_quarter is not null
group by introduced_quarter, congress
order by introduced_quarter desc
