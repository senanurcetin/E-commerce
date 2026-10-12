-- Fail if a row's financial metrics do not match its current order status.
-- Null-safe comparisons work in both BigQuery and DuckDB.
with expected as (
    select
        order_item_sk,
        order_item_status,
        sale_price,
        revenue,
        returned_revenue,
        is_completed_order,
        is_returned_order,
        case when lower(order_item_status) = 'complete' then sale_price else 0 end as expected_revenue,
        case when lower(order_item_status) = 'returned' then sale_price else 0 end as expected_returned_revenue,
        case when lower(order_item_status) = 'complete' then 1 else 0 end as expected_completed_flag,
        case when lower(order_item_status) = 'returned' then 1 else 0 end as expected_returned_flag
    from {{ ref('fct_order_marketing') }}
)
select order_item_sk, order_item_status
from expected
where revenue is distinct from expected_revenue
   or returned_revenue is distinct from expected_returned_revenue
   or is_completed_order is distinct from expected_completed_flag
   or is_returned_order is distinct from expected_returned_flag
