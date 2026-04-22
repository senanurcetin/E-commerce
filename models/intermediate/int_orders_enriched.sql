with order_items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

joined as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.user_id,
        oi.product_id,
        oi.order_status,
        oi.sale_price,
        oi.created_at as order_item_created_at,
        oi.shipped_at,
        oi.delivered_at,
        oi.returned_at,

        p.product_name,
        coalesce(p.product_name, 'Unknown Product') as product_name_reporting,
        p.category,
        p.brand,
        p.department,
        p.retail_price,
        p.cost,

        u.gender,
        u.age,
        u.country,
        u.traffic_source as user_acquisition_source
    from order_items oi
    left join products p
        on oi.product_id = p.product_id
    left join users u
        on oi.user_id = u.user_id
)

select * from joined