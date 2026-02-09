select
    committee_id,
    bioguide_id,
    role
from {{ source('raw', 'committee_members') }}
