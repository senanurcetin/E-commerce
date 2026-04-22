with order_items as (

    select *
    from {{ ref('stg_order_items') }}

),

products as (

    select *
    from {{ ref('stg_products') }}

),

users as (

    select *
    from {{ ref('stg_users') }}

),

final as (

    select
        oi.order_item_id,
        oi.order_id,
        oi.user_id,
        oi.product_id,
        oi.inventory_item_id,
        oi.order_item_status,
        oi.order_item_created_at,
        oi.order_item_shipped_at,
        oi.order_item_delivered_at,
        oi.order_item_returned_at,
        oi.sale_price,

        p.product_name,
        p.category,
        p.brand,
        p.department,
        p.cost,
        p.retail_price,

        u.gender,
        u.country,
        u.signup_traffic_source

    from order_items oi
    left join products p
        on oi.product_id = p.product_id
    left join users u
        on oi.user_id = u.user_id

)

select *
from final