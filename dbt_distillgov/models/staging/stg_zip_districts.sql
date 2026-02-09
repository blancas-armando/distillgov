select
    zcta,
    state,
    district
from {{ source('raw', 'zip_districts') }}
