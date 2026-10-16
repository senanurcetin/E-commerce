{{ config(severity='warn') }}

-- Data-quality flag, not a model check: in the Google Sheets export the refund figure is
-- higher than the order revenue on most orders, so it cannot be a refunded amount.
select
    o.orders_id,
    o.revenue,
    r.refund_amount
from {{ ref('stg_gsheet__orders') }} as o
inner join {{ ref('stg_gsheet__refund') }} as r
    on o.orders_id = r.orders_id
where r.refund_amount > o.revenue
