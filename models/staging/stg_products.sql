with source as (

    select *
    from {{ source('e_ticaret_raw', 'products') }}

),

renamed as (

    select
        cast(id as int64) as product_id,
        cast(cost as numeric) as cost,
        cast(retail_price as numeric) as retail_price,

        coalesce(lower(nullif(trim(category), '')), 'unknown') as category,
        coalesce(nullif(trim(name), ''), 'unknown') as product_name,
        coalesce(nullif(trim(brand), ''), 'unknown') as brand,
        coalesce(lower(nullif(trim(department), '')), 'unknown') as department,
        coalesce(nullif(trim(sku), ''), 'unknown') as sku,

        cast(distribution_center_id as int64) as distribution_center_id

    from source
    where id is not null

)

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
from renamed