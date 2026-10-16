{{ config(enabled=var('source_system', 'gwz_raw') == 'fvt_gsheet', tags=['fvt_gsheet']) }}

-- fvt_gsheet only. The sheet's `refund` column does not behave like refunded money (it is on every
-- order, 50-500 and independent of the order size), so it is reported on its own and is NOT
-- subtracted from revenue or any margin. net_revenue_after_refunds stays NULL until the unit is
-- confirmed and refund_unit_verified is set (see README, "Refunds").
with orders as (
    select
        o.date_date,
        o.revenue,
        r.refund_amount as refund_raw,
        r.refund_amount * {{ var('refund_amount_scale', 1.0) }} as refund_scaled
    from {{ ref('stg_gsheet__orders') }} as o
    left join {{ ref('stg_gsheet__refund') }} as r
        on o.orders_id = r.orders_id
)

select
    {{ month_start('date_date') }} as datemonth,
    count(*) as orders,
    round(sum(revenue), 2) as revenue,
    round(sum(coalesce(refund_raw, 0)), 2) as refund_amount_raw,
    round(sum(coalesce(refund_scaled, 0)), 2) as refund_amount,
    sum(case when refund_raw > 0 then 1 else 0 end) as orders_with_refund,
    sum(case when refund_scaled > revenue then 1 else 0 end) as orders_refund_above_revenue,
    round({{ dbt_utils.safe_divide('sum(coalesce(refund_scaled, 0))', 'sum(revenue)') }}, 4) as refund_to_revenue,
    {{ 'true' if var('refund_unit_verified', false) else 'false' }} as refund_unit_verified,
    {% if var('refund_unit_verified', false) %}
        round(sum(revenue) - sum(coalesce(refund_scaled, 0)), 2)
    {% else %}
        cast(null as {{ dbt.type_numeric() }})
    {% endif %} as net_revenue_after_refunds
from orders
group by datemonth
