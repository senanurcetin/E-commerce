with source as (

    select *
    {% if target.type == 'bigquery' %}
    from {{ source('e_ticaret_raw', 'products') }}
    {% else %}
    from {{ ref('products') }}
    {% endif %}

),

renamed as (

    select
        cast(id as {{ dbt.type_bigint() }}) as product_id,
        cast(cost as {{ dbt.type_numeric() }}) as cost,
        cast(retail_price as {{ dbt.type_numeric() }}) as retail_price,

        coalesce(lower(nullif(trim(category), '')), 'unknown') as category,
        coalesce(nullif(trim(name), ''), 'unknown') as product_name,
        coalesce(nullif(trim(brand), ''), 'unknown') as brand,
        coalesce(lower(nullif(trim(department), '')), 'unknown') as department,
        coalesce(nullif(trim(sku), ''), 'unknown') as sku,

        cast(distribution_center_id as {{ dbt.type_bigint() }}) as distribution_center_id

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
