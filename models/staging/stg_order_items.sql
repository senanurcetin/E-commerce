with source as (

    select *
    from {{ source('e_ticaret_raw', 'order_items') }}

),

renamed as (

    select
        cast(id as int64) as order_item_id,
        cast(order_id as int64) as order_id,
        cast(user_id as int64) as user_id,
        cast(product_id as int64) as product_id,
        cast(inventory_item_id as int64) as inventory_item_id,

        coalesce(lower(nullif(trim(status), '')), 'unknown') as order_item_status,

        cast(created_at as timestamp) as order_item_created_at,
        cast(shipped_at as timestamp) as order_item_shipped_at,
        cast(delivered_at as timestamp) as order_item_delivered_at,
        cast(returned_at as timestamp) as order_item_returned_at,

        cast(sale_price as numeric) as sale_price

    from source
    where id is not null

)

select
    order_item_id,
    order_id,
    user_id,
    product_id,
    inventory_item_id,
    order_item_status,
    order_item_created_at,
    order_item_shipped_at,
    order_item_delivered_at,
    order_item_returned_at,
    sale_price
from renamed