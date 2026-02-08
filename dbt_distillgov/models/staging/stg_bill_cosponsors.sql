select
    bill_id,
    bioguide_id,
    cosponsor_date,
    is_original
from {{ source('raw', 'bill_cosponsors') }}
