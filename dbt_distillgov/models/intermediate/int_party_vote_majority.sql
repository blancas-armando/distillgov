-- For each vote + party, determine the majority position.
-- Normalizes House (Yes/No) and Senate (Yea/Nay) to a common Yes/No.

with normalized_votes as (
    select
        mv.vote_id,
        mv.bioguide_id,
        case
            when mv.position in ('Yes', 'Yea') then 'Yes'
            when mv.position in ('No', 'Nay') then 'No'
            else mv.position
        end as position,
        m.party
    from {{ ref('stg_member_votes') }} mv
    inner join {{ ref('stg_members') }} m on mv.bioguide_id = m.bioguide_id
    where mv.position in ('Yes', 'Yea', 'No', 'Nay')
      and m.party in ('D', 'R')
),

position_counts as (
    select
        vote_id,
        party,
        position,
        count(*) as cnt
    from normalized_votes
    group by vote_id, party, position
),

ranked as (
    select
        vote_id,
        party,
        position as majority_position,
        cnt,
        sum(cnt) over (partition by vote_id, party) as total,
        row_number() over (partition by vote_id, party order by cnt desc) as rn
    from position_counts
)

select
    vote_id,
    party,
    majority_position
from ranked
where rn = 1
  and cnt * 2 > total  -- Exclude exact 50/50 ties (no meaningful majority)
