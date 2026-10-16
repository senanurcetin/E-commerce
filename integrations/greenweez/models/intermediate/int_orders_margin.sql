{% if var('source_system', 'gwz_raw') == 'fvt_gsheet' %}
-- fvt_gsheet: order-level export. No product lines, so quantity is unknown (NULL)
-- and margin is revenue - purchase_cost straight from the order row.
select
    orders_id,
    date_date,
    revenue,
    cast(null as {{ dbt.type_int() }}) as quantity,
    purchase_cost,
    (revenue - purchase_cost) as margin
from {{ ref('stg_gsheet__orders') }}
{% else %}
    select
        orders_id,
        date_date,
        sum(revenue) as revenue,
        sum(quantity) as quantity,
        sum(purchase_cost) as purchase_cost,
        sum(margin) as margin
    from {{ ref('int_sales_margin') }}
    group by orders_id, date_date
{% endif %}
