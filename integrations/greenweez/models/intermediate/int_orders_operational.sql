-- Orders without a shipping record (or with unpriced product lines) contribute 0
-- for the missing components instead of turning operational_margin into NULL,
-- which would silently drop the order from every daily/monthly total.
with ship as (
    {% if var('source_system', 'gwz_raw') == 'fvt_gsheet' %}
    -- fvt_gsheet: the customer-paid fee lives on the order row, costs in the shipping sheet
    select
        o.orders_id,
        o.shipping_fee,
        s.log_cost,
        s.ship_cost,
        (s.orders_id is not null) as has_ship_record
    from {{ ref('stg_gsheet__orders') }} as o
    left join {{ ref('stg_gsheet__shipping') }} as s
        on o.orders_id = s.orders_id
    {% else %}
        select
            orders_id,
            shipping_fee,
            log_cost,
            ship_cost,
            true as has_ship_record
        from {{ ref('stg_raw__ship') }}
    {% endif %}
)

select
    o.orders_id,
    o.date_date,
    o.revenue,
    o.quantity,
    o.purchase_cost,
    o.margin,
    coalesce(s.shipping_fee, 0) as shipping_fee,
    coalesce(s.log_cost, 0) as log_cost,
    coalesce(s.ship_cost, 0) as ship_cost,
    coalesce(s.has_ship_record, false) as has_ship_record,
    (
        coalesce(o.margin, 0)
        + coalesce(s.shipping_fee, 0)
        - coalesce(s.log_cost, 0)
        - coalesce(s.ship_cost, 0)
    ) as operational_margin
from {{ ref('int_orders_margin') }} as o
left join ship as s
    on o.orders_id = s.orders_id
