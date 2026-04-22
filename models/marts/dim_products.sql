with products as (

    select *
    from {{ ref('stg_products') }}

),

final as (

    select
        product_id,
        cost,
        retail_price,
        category,
        product_name,
        brand,
        department,
        sku,
        distribution_center_id

    from products

)

select *
from final