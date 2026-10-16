select
    cast(date_date as date) as date_date,
    cast(orders_id as {{ dbt.type_int() }}) as orders_id,
    cast(pdt_id as {{ dbt.type_int() }}) as products_id,
    cast(revenue as {{ dbt.type_numeric() }}) as revenue,
    cast(quantity as {{ dbt.type_int() }}) as quantity
from {{ source('raw', 'sales') }}
