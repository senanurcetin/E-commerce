with products as (
    select * from {{ ref('stg_products') }}
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
        category, brand, department, cost, retail_price,
        {% if target.type == 'bigquery' %}
        safe_subtract(retail_price, cost) as unit_margin,
        safe_divide(retail_price - cost, retail_price) as unit_margin_pct,
        {% else %}
        (retail_price - cost) as unit_margin,
        case when retail_price <> 0 then (retail_price - cost) / retail_price else null end as unit_margin_pct,
        {% endif %}
        sku, distribution_center_id
    from products
)
select * from final
