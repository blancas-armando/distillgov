select
    vote_id,
    bioguide_id,
    position
from {{ source('raw', 'member_votes') }}
