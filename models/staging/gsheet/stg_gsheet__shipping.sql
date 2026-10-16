select
    cast(orders_id as {{ dbt.type_int() }}) as orders_id,
    cast(date_date as date) as date_date,
    cast(log_cost as {{ dbt.type_numeric() }}) as log_cost,
    cast(ship_cost as {{ dbt.type_numeric() }}) as ship_cost
from {{ source('gsheet', 'shipping') }}
