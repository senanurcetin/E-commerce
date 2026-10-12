-- A sale price must exist and must not be negative for every order item.
-- Report invalid inputs even when the order has not yet been completed.
select order_item_sk, sale_price
from {{ ref('fct_order_marketing') }}
where sale_price is null or sale_price < 0
