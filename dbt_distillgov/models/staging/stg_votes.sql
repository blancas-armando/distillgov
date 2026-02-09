select
    vote_id,
    congress,
    chamber,
    session,
    roll_call,
    vote_date,
    question,
    description,
    result,
    bill_id,
    yea_count,
    nay_count,
    present_count,
    not_voting,
    updated_at,
    case
        when question ilike '%passage%'
          or question ilike '%pass%'
          or question ilike '%conference report%'
          or question ilike '%override%'
          or question ilike '%concur%'
          or question ilike '%adopt%'
          or question ilike '%ratif%'
        then true
        else false
    end as is_passage
from {{ source('raw', 'votes') }}
