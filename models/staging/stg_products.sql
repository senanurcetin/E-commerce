with source as (

    select *
    from {{ source('e_ticaret_raw', 'products') }}

),

renamed as (

    select
        cast(id as int64) as product_id,
        cast(cost as numeric) as cost,
        trim(category) as category,
        trim(name) as product_name,
        trim(brand) as brand,
        cast(retail_price as numeric) as retail_price,
        trim(department) as department,
        cast(sku as string) as sku,
        cast(distribution_center_id as int64) as distribution_center_id
    from source

)

select *
from renamed