select
    trade_id,
    bioguide_id,
    transaction_date,
    disclosure_date,
    ticker,
    asset_name,
    asset_type,
    trade_type,
    amount_low,
    amount_high,
    owner,
    ptr_link,
    comment,
    updated_at
from {{ source('raw', 'trades') }}
