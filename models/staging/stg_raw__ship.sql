select
    cast(orders_id as {{ dbt.type_int() }}) as orders_id,
    cast(shipping_fee as {{ dbt.type_numeric() }}) as shipping_fee,
    cast(logCost as {{ dbt.type_numeric() }}) as log_cost,
    cast(ship_cost as {{ dbt.type_numeric() }}) as ship_cost
from {{ source('raw', 'ship') }}
