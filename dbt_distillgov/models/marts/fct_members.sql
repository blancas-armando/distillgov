{{
    config(materialized='table')
}}

with sponsorship_stats as (
    select
        sponsor_id,
        count(*) as bills_sponsored,
        count(*) filter (where status = 'enacted') as bills_enacted,
        count(*) filter (where status in ('passed_house', 'passed_senate', 'passed_both', 'enacted')) as bills_passed
    from {{ ref('stg_bills') }}
    where sponsor_id is not null
    group by sponsor_id
),

voting_stats as (
    select
        mv.bioguide_id,
        count(*) as votes_cast,
        count(*) filter (where mv.position = 'Not Voting') as votes_missed,
        round(
            100.0 * count(*) filter (where mv.position != 'Not Voting') / nullif(count(*), 0),
            1
        ) as attendance_rate
    from {{ ref('stg_member_votes') }} mv
    group by mv.bioguide_id
),

trade_stats as (
    select
        bioguide_id,
        count(*) as disclosure_count
    from {{ ref('stg_trades') }}
    group by bioguide_id
)

select
    -- Keys
    m.bioguide_id,

    -- Core fields
    m.first_name,
    m.last_name,
    m.full_name,
    m.party,
    m.state,
    m.district,
    m.chamber,
    m.is_current,
    m.image_url,
    m.leadership_role,
    m.start_date,

    -- Sponsorship stats
    coalesce(s.bills_sponsored, 0) as bills_sponsored,
    coalesce(s.bills_enacted, 0) as bills_enacted,
    coalesce(s.bills_passed, 0) as bills_passed,
    case
        when coalesce(s.bills_sponsored, 0) > 0
        then round(100.0 * coalesce(s.bills_enacted, 0) / s.bills_sponsored, 1)
        else 0
    end as sponsor_success_rate,

    -- Voting stats
    coalesce(v.votes_cast, 0) as votes_cast,
    coalesce(v.votes_missed, 0) as votes_missed,
    v.attendance_rate,

    -- Trading stats
    coalesce(t.disclosure_count, 0) as disclosure_count

from {{ ref('stg_members') }} m
left join sponsorship_stats s on m.bioguide_id = s.sponsor_id
left join voting_stats v on m.bioguide_id = v.bioguide_id
left join trade_stats t on m.bioguide_id = t.bioguide_id
