-- Top products by revenue and return rate
-- Answers: which products drive the most value and which have quality issues?

with product_metrics as (
    select
        product_id,
        product_name,
        category,
        brand,
        department,
        count(distinct order_id)                                           as total_orders,
        sum(revenue)                                                       as gross_revenue,
        sum(returned_revenue)                                              as returned_revenue,
        sum(revenue) - sum(returned_revenue)                               as net_revenue,
        sum(is_returned_order)                                             as return_count,
        round(sum(is_returned_order) * 100.0 / nullif(count(*), 0), 1)   as return_rate_pct,
        round(avg(sale_price), 2)                                          as avg_sale_price
    from {{ ref('fct_order_marketing') }}
    group by product_id, product_name, category, brand, department
)

select
    product_id,
    product_name,
    category,
    brand,
    total_orders,
    round(gross_revenue, 2)  as gross_revenue,
    round(net_revenue, 2)    as net_revenue,
    return_rate_pct,
    avg_sale_price,
    rank() over (order by net_revenue desc)     as revenue_rank,
    rank() over (order by return_rate_pct desc) as return_risk_rank
from product_metrics
order by net_revenue desc
