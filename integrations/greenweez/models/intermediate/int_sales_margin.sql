select
    s.orders_id,
    s.date_date,
    s.products_id,
    s.revenue,
    s.quantity,
    p.purchase_price,
    (s.quantity * p.purchase_price) as purchase_cost,
    (s.revenue - (s.quantity * p.purchase_price)) as margin
from {{ ref('stg_raw__sales') }} as s
left join {{ ref('stg_raw__product') }} as p
    on s.products_id = p.products_id
