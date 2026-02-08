select
    bill_type,
    congress,
    count(*) as total,
    count(*) filter (where is_enacted) as enacted,
    round(100.0 * count(*) filter (where is_enacted) / count(*), 2) as enactment_rate_pct
from {{ ref('fct_bills') }}
group by bill_type, congress
order by congress desc, total desc
