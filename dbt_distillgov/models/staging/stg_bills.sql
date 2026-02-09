select
    bill_id,
    congress,
    bill_type,
    bill_number,
    title,
    short_title,
    introduced_date,
    sponsor_id,
    policy_area,
    origin_chamber,
    latest_action,
    latest_action_date,
    status,
    summary,
    full_text_url,
    updated_at
from {{ source('raw', 'bills') }}
