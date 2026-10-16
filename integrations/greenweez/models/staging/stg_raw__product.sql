select
    cast(products_id as {{ dbt.type_int() }}) as products_id,
    cast(purchse_PRICE as {{ dbt.type_numeric() }}) as purchase_price
from {{ source('raw', 'product') }}
