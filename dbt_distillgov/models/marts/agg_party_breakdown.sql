select
    sponsor_party as party,
    congress,
    count(*) as bills_sponsored,
    count(*) filter (where is_enacted) as enacted,
    count(*) filter (where is_passed) as passed,
    round(100.0 * count(*) filter (where is_enacted) / count(*), 2) as enactment_rate_pct
from {{ ref('fct_bills') }}
where sponsor_party is not null
group by sponsor_party, congress
order by congress desc, party
