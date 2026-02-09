{{
    config(materialized='table')
}}

with sponsorship_stats as (
    select
        sponsor_id,
        count(*) as bills_sponsored,
        count(*) filter (where status = 'enacted') as bills_enacted,
        count(*) filter (where status in ('passed_house', 'passed_senate', 'enacted')) as bills_passed
    from {{ ref('stg_bills') }}
    where sponsor_id is not null
    group by sponsor_id
),

voting_stats as (
    select
        mv.bioguide_id,
        count(*) as total_roll_calls,
        count(*) filter (where mv.position = 'Not Voting') as votes_missed,
        round(
            100.0 * count(*) filter (where mv.position != 'Not Voting') / nullif(count(*), 0),
            1
        ) as attendance_rate
    from {{ ref('stg_member_votes') }} mv
    group by mv.bioguide_id
),

party_loyalty as (
    select
        mv.bioguide_id,
        round(
            100.0 * count(*) filter (
                where case
                    when mv.position in ('Yes', 'Yea') then 'Yes'
                    when mv.position in ('No', 'Nay') then 'No'
                end = pvm.majority_position
            ) / nullif(count(*), 0),
            1
        ) as party_loyalty_pct
    from {{ ref('stg_member_votes') }} mv
    inner join {{ ref('stg_members') }} m on mv.bioguide_id = m.bioguide_id
    inner join {{ ref('int_party_vote_majority') }} pvm
        on mv.vote_id = pvm.vote_id and m.party = pvm.party
    where mv.position in ('Yes', 'Yea', 'No', 'Nay')
    group by mv.bioguide_id
),

base as (
    select
        m.bioguide_id,
        m.first_name,
        m.last_name,
        m.full_name,
        m.party,
        m.state,
        m.district,
        m.chamber,
        m.is_current,
        m.image_url,
        m.official_url,
        m.leadership_role,
        m.start_date,
        coalesce(s.bills_sponsored, 0) as bills_sponsored,
        coalesce(s.bills_enacted, 0) as bills_enacted,
        coalesce(s.bills_passed, 0) as bills_passed,
        case
            when coalesce(s.bills_sponsored, 0) > 0
            then round(100.0 * coalesce(s.bills_enacted, 0) / s.bills_sponsored, 1)
            else 0
        end as sponsor_success_rate,
        coalesce(v.total_roll_calls, 0) as total_roll_calls,
        coalesce(v.votes_missed, 0) as votes_missed,
        v.attendance_rate,
        pl.party_loyalty_pct
    from {{ ref('stg_members') }} m
    left join sponsorship_stats s on m.bioguide_id = s.sponsor_id
    left join voting_stats v on m.bioguide_id = v.bioguide_id
    left join party_loyalty pl on m.bioguide_id = pl.bioguide_id
)

select
    *,
    -- Composite activity score (0-100): percentile rank across current members
    -- on sponsorship, voting volume, and attendance, averaged
    case when is_current then
        round((
            percent_rank() over (partition by is_current order by bills_sponsored) * 100
            + percent_rank() over (partition by is_current order by total_roll_calls) * 100
            + percent_rank() over (partition by is_current order by coalesce(attendance_rate, 0)) * 100
        ) / 3.0, 1)
    end as activity_score
from base
