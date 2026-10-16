select
    date_date,
    count(orders_id) as total_transactions,
    round(sum(revenue), 2) as total_revenue,
    round({{ dbt_utils.safe_divide('sum(revenue)', 'count(orders_id)') }}, 2) as avg_basket,
    round(sum(operational_margin), 2) as operational_margin,
    round(sum(purchase_cost), 2) as total_purchase_cost,
    round(sum(margin), 2) as total_margin,
    round(sum(shipping_fee), 2) as total_shipping_fee,
    round(sum(log_cost), 2) as total_log_cost,
    round(sum(ship_cost), 2) as total_ship_cost,
    sum(quantity) as total_quantity
from {{ ref('int_orders_operational') }}
group by date_date
