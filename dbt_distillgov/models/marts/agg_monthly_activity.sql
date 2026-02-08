select
    introduced_month as month,
    congress,
    count(*) as bills_introduced,
    count(*) filter (where is_enacted) as bills_enacted,
    count(*) filter (where is_passed) as bills_passed,
    count(*) filter (where sponsor_party = 'D') as dem_sponsored,
    count(*) filter (where sponsor_party = 'R') as rep_sponsored
from {{ ref('fct_bills') }}
where introduced_month is not null
group by introduced_month, congress
order by introduced_month desc
