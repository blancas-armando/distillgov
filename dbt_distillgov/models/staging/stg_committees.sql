select
    committee_id,
    name,
    chamber,
    committee_type,
    parent_id,
    url
from {{ source('raw', 'committees') }}
