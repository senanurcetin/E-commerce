select
    cast(orders_id as {{ dbt.type_int() }}) as orders_id,
    cast(substr(datetime, 1, 10) as date) as date_date,
    cast(refund as {{ dbt.type_numeric() }}) as refund_amount
from {{ source('gsheet', 'refund') }}
