select
    bioguide_id,
    first_name,
    last_name,
    full_name,
    party,
    state,
    district,
    chamber,
    is_current,
    image_url,
    official_url,
    leadership_role,
    start_date,
    updated_at
from {{ source('raw', 'members') }}
