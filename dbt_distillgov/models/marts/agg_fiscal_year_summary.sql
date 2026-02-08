select
    fiscal_year,
    count(*) as bills_introduced,
    count(*) filter (where is_enacted) as enacted,
    count(*) filter (where is_passed) as passed,
    round(100.0 * count(*) filter (where is_enacted) / count(*), 2) as enactment_rate_pct
from {{ ref('fct_bills') }}
where fiscal_year is not null
group by fiscal_year
order by fiscal_year desc
