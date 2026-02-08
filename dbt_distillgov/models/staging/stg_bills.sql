select
    bill_id,
    congress,
    bill_type,
    bill_number,
    title,
    introduced_date,
    sponsor_id,
    policy_area,
    origin_chamber,
    latest_action,
    latest_action_date,
    status,
    updated_at
from {{ source('raw', 'bills') }}
