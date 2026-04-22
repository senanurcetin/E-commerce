{{ config(materialized='view') }}

with events as (

    select *
    from {{ ref('int_events_enriched') }}
    where session_id is not null
      and user_id is not null

),

sessions as (

    select
        session_id,
        user_id,
        min(event_created_at) as session_start_at,
        max(event_created_at) as session_end_at,
        timestamp_diff(max(event_created_at), min(event_created_at), second) as session_duration_seconds,
        count(*) as total_events,
        countif(event_type = 'page_view') as page_view_events,
        countif(event_type = 'purchase') as purchase_events,
        countif(event_type = 'cancel') as cancel_events,
        any_value(traffic_source) as traffic_source,
        any_value(browser) as browser
    from events
    group by session_id, user_id

),

users as (

    select *
    from {{ ref('dim_user') }}

),

orders as (

    select *
    from {{ ref('int_orders_enriched') }}
    where user_id is not null

),

order_summary as (

    select
        user_id,
        count(distinct order_id) as total_orders,
        count(distinct case when order_item_status = 'complete' then order_id end) as completed_orders,
        sum(case when order_item_status = 'complete' then sale_price else 0 end) as revenue,
        sum(case when order_item_status = 'returned' then sale_price else 0 end) as returned_revenue
    from orders
    group by user_id

),

final as (

    select
        s.session_id,
        s.user_id,

        s.session_start_at,
        s.session_end_at,

        datetime(s.session_start_at, "Europe/Istanbul") as session_start_at_local,
        datetime(s.session_end_at, "Europe/Istanbul") as session_end_at_local,

        date(datetime(s.session_start_at, "Europe/Istanbul")) as session_date,
        extract(hour from datetime(s.session_start_at, "Europe/Istanbul")) as session_hour,

        s.session_duration_seconds,
        s.total_events,
        s.page_view_events,
        s.purchase_events,
        s.cancel_events,
        s.traffic_source,
        s.browser,

        u.age_segment,
        u.gender,
        u.country,
        u.state,

        coalesce(o.total_orders, 0) as total_orders,
        coalesce(o.completed_orders, 0) as completed_orders,
        coalesce(o.revenue, 0) as revenue,
        coalesce(o.returned_revenue, 0) as returned_revenue

    from sessions s
    left join users u
        on s.user_id = u.user_id
    left join order_summary o
        on s.user_id = o.user_id

)

select *
from final