-- Channel performance: revenue, orders, and conversion rate by marketing channel
-- Run against fct_order_marketing + fct_marketing_web_performance

with orders as (
    select
        channel_group,
        traffic_source,
        sum(revenue)                                          as total_revenue,
        sum(returned_revenue)                                 as total_returns,
        sum(revenue) - sum(returned_revenue)                  as net_revenue,
        count(distinct order_id)                              as total_orders,
        count(distinct case when is_completed_order = 1 then order_id end) as completed_orders,
        count(distinct case when is_returned_order  = 1 then order_id end) as returned_orders
    from {{ ref('fct_order_marketing') }}
    group by channel_group, traffic_source
),

sessions as (
    select
        channel_group,
        traffic_source,
        count(distinct session_id)                            as total_sessions,
        sum(is_converted)                                     as converted_sessions,
        round(avg(session_duration_minutes), 2)               as avg_session_duration_min,
        round(avg(page_view_events), 1)                       as avg_page_views
    from {{ ref('fct_marketing_web_performance') }}
    group by channel_group, traffic_source
),

final as (
    select
        coalesce(o.channel_group, s.channel_group)            as channel_group,
        coalesce(o.traffic_source, s.traffic_source)          as traffic_source,
        coalesce(s.total_sessions, 0)                         as sessions,
        coalesce(o.completed_orders, 0)                       as orders,
        round(coalesce(o.net_revenue, 0), 2)                  as net_revenue,
        case
            when coalesce(s.total_sessions, 0) > 0
            then round(coalesce(s.converted_sessions, 0) * 100.0 / s.total_sessions, 2)
            else 0
        end                                                    as conversion_rate_pct,
        round(coalesce(s.avg_session_duration_min, 0), 2)     as avg_session_duration_min,
        round(coalesce(s.avg_page_views, 0), 1)               as avg_page_views,
        coalesce(o.returned_orders, 0)                        as returned_orders
    from orders o
    full outer join sessions s
        on o.channel_group  = s.channel_group
       and o.traffic_source = s.traffic_source
)

select *
from final
order by net_revenue desc
