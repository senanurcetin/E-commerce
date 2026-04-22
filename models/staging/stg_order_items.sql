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
        lower(trim(status)) as order_status,
        cast(created_at as timestamp) as created_at,
        cast(shipped_at as timestamp) as shipped_at,
        cast(delivered_at as timestamp) as delivered_at,
        cast(returned_at as timestamp) as returned_at,
        cast(sale_price as numeric) as sale_price
    from source

)

select *
from renamed