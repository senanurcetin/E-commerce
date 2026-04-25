with products as (

    select *
    from {{ ref('stg_products') }}

),

final as (

    select
        product_id,
        case
            when product_name != 'unknown' then product_name
            when brand != 'unknown' and category != 'unknown' then concat(brand, ' - ', category)
            when brand != 'unknown' then brand
            when category != 'unknown' then category
            when sku != 'unknown' then concat('sku-', substr(sku, 1, 8))
            else 'unknown'
        end as product_name,
        category,
        brand,
        department,
        cost,
        retail_price,
        safe_subtract(retail_price, cost) as unit_margin,
        safe_divide(retail_price - cost, retail_price) as unit_margin_pct,
        sku,
        distribution_center_id
    from products

)

select *
from final
