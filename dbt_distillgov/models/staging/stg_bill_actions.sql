select
    bill_id,
    action_date,
    action_text,
    action_type,
    chamber,
    sequence
from {{ source('raw', 'bill_actions') }}
