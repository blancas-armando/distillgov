select
    bill_id,
    subject
from {{ source('raw', 'bill_subjects') }}
