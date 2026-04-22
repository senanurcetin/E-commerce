{{ config(materialized='view') }}

with orders as (

    select *
    from {{ ref('int_orders_enriched') }}
    where user_id is not null

),

users as (

    select *
    from {{ ref('dim_user') }}

),

final as (

    select
        order_item_id,
        order_id,
        user_id,
        product_id,
        order_item_status,
        order_item_created_at,
        sale_price,
        product_name,
        category,
        brand,
        department,
        gender,
        country,
        signup_traffic_source as traffic_source

    from orders

)

select *
from final