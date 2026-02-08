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
    updated_at
from {{ source('raw', 'votes') }}
