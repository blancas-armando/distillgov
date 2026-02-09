{{
    config(materialized='table')
}}

with cosponsorship as (
    select
        c.bill_id,
        count(*) as total_cosponsors,
        count(*) filter (where m.party = 'D') as dem_cosponsors,
        count(*) filter (where m.party = 'R') as rep_cosponsors,
        count(*) filter (where m.party not in ('D', 'R')) as ind_cosponsors
    from {{ ref('stg_bill_cosponsors') }} c
    left join {{ ref('stg_members') }} m on c.bioguide_id = m.bioguide_id
    group by c.bill_id
)

select
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

    -- Sponsor info (denormalized)
    m.full_name as sponsor_name,
    m.party as sponsor_party,
    m.state as sponsor_state,

    -- Cosponsorship
    coalesce(cs.total_cosponsors, 0) as total_cosponsors,
    coalesce(cs.dem_cosponsors, 0) as dem_cosponsors,
    coalesce(cs.rep_cosponsors, 0) as rep_cosponsors,
    coalesce(cs.ind_cosponsors, 0) as ind_cosponsors,
    coalesce(cs.dem_cosponsors, 0) > 0 and coalesce(cs.rep_cosponsors, 0) > 0 as is_bipartisan,

    -- Time dimensions
    date_trunc('week', b.introduced_date) as introduced_week,
    date_trunc('month', b.introduced_date) as introduced_month,
    date_trunc('quarter', b.introduced_date) as introduced_quarter,
    extract(year from b.introduced_date) as introduced_year,

    -- Fiscal year (Oct 1 - Sep 30)
    case
        when extract(month from b.introduced_date) >= 10
        then extract(year from b.introduced_date)::integer + 1
        else extract(year from b.introduced_date)::integer
    end as fiscal_year,

    -- Congressional session (1 = odd year, 2 = even year)
    case
        when extract(year from b.introduced_date)::integer % 2 = 1 then 1
        else 2
    end as session,

    -- Computed metrics
    datediff('day', b.introduced_date, current_date) as days_since_introduced,
    datediff('day', b.introduced_date, b.latest_action_date) as days_active,

    -- Status flags
    b.status = 'enacted' as is_enacted,
    b.status in ('passed_house', 'passed_senate') as is_passed,
    b.status = 'in_committee' as is_in_committee,
    b.status = 'introduced' as is_new,
    coalesce(datediff('day', b.latest_action_date, current_date) > 90, false) as is_stale,
    coalesce(datediff('day', b.latest_action_date, current_date) <= 30, false) as is_recently_active

from {{ ref('stg_bills') }} b
left join {{ ref('stg_members') }} m on b.sponsor_id = m.bioguide_id
left join cosponsorship cs on b.bill_id = cs.bill_id
