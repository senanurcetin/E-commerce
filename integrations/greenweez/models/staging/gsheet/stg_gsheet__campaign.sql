select
    cast(substr(datetime, 1, 10) as date) as date_date,
    cast(cost as {{ dbt.type_numeric() }}) as ads_cost
from {{ source('gsheet', 'campaign') }}
