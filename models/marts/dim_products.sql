with products as (

    select *
    from {{ ref('stg_products') }}

),

final as (

    select
        product_id,
        product_name,
        category,
        brand,
        department,
        cost,
        retail_price,
        safe_subtract(retail_price, cost) as unit_margin,
        sku,
        distribution_center_id
    from products

)

select *
from final