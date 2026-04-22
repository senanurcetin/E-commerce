select *
from {{ ref('fct_order_marketing') }}
where revenue < 0
   or returned_revenue < 0