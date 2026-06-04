{{
    config(
        materialized = 'incremental',
        unique_key   = 'order_item_sk',
        on_schema_change = 'sync_all_columns'
    )
}}

with orders as (
    select * from {{ ref('int_orders_enriched') }}
    where user_id is not null
    {% if is_incremental() %}
      -- on incremental runs, only process new or updated order items
      and order_item_created_at > (select max(order_item_created_at) from {{ this }})
    {% endif %}
),
final as (
    select
        concat(cast(order_item_id as {{ dbt.type_string() }}), '-', cast(order_id as {{ dbt.type_string() }})) as order_item_sk,
        order_item_id, order_id, user_id, product_id, order_item_status, order_item_created_at,
        {% if target.type == 'bigquery' %}
        datetime(order_item_created_at, "Europe/Istanbul") as order_item_created_at_local,
        date(datetime(order_item_created_at, "Europe/Istanbul")) as order_date,
        extract(hour from datetime(order_item_created_at, "Europe/Istanbul")) as order_hour,
        {% else %}
        order_item_created_at as order_item_created_at_local,
        cast(order_item_created_at as date) as order_date,
        extract(hour from order_item_created_at) as order_hour,
        {% endif %}
        sale_price,
        case when lower(order_item_status) = 'complete' then sale_price else 0 end as revenue,
        case when lower(order_item_status) = 'returned' then sale_price else 0 end as returned_revenue,
        case when lower(order_item_status) = 'complete' then 1 else 0 end as is_completed_order,
        case when lower(order_item_status) = 'returned' then 1 else 0 end as is_returned_order,
        product_name, category, brand, department, gender, country,
        traffic_source,
        {{ marketing_channel_group('traffic_source') }} as channel_group
    from orders
)
select * from final
