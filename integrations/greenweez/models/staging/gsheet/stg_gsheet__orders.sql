select
    cast(orders_id as {{ dbt.type_int() }}) as orders_id,
    cast(substr(datetime, 1, 10) as date) as date_date,
    cast(turnover as {{ dbt.type_numeric() }}) as revenue,
    cast(purchase_cost as {{ dbt.type_numeric() }}) as purchase_cost,
    cast(ship_fee as {{ dbt.type_numeric() }}) as shipping_fee
from {{ source('gsheet', 'orders') }}
