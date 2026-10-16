{{ config(enabled=var('source_system', 'gwz_raw') == 'fvt_gsheet') }}

-- fvt_gsheet only: the refund mart must cover the same orders and revenue as the finance mart, and its
-- raw refund total must equal the staging total.
{% if var('source_system', 'gwz_raw') == 'fvt_gsheet' %}
    with refunds as (
        select
            sum(orders) as orders,
            sum(revenue) as revenue,
            sum(refund_amount_raw) as refund_amount_raw
        from {{ ref('finance_refunds_month') }}
    ),

    finance as (
        select
            sum(transactions) as orders,
            sum(revenue) as revenue
        from {{ ref('finance_campaigns_month') }}
    ),

    staged as (
        select sum(refund_amount) as refund_amount_raw
        from {{ ref('stg_gsheet__refund') }}
    )

    select
        r.orders,
        f.orders as finance_orders
    from refunds as r
    cross join finance as f
    cross join staged as s
    where
        r.orders != f.orders
        or abs(r.revenue - f.revenue) > 0.5
        or abs(r.refund_amount_raw - s.refund_amount_raw) > 0.5
{% else %}
select 1 as unused where 1 = 0
{% endif %}
