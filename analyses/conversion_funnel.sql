-- Conversion funnel: page_view -> cart -> purchase drop-off by channel
-- Answers: where do users drop off, and which channels convert best?

with funnel_events as (
    select
        session_id,
        channel_group,
        max(case when event_type = 'page_view' then 1 else 0 end) as reached_page_view,
        max(case when event_type = 'cart'      then 1 else 0 end) as reached_cart,
        max(case when event_type = 'purchase'  then 1 else 0 end) as reached_purchase
    from {{ ref('int_events_enriched') }}
    group by session_id, channel_group
),

funnel_summary as (
    select
        channel_group,
        count(distinct session_id)                                         as total_sessions,
        sum(reached_page_view)                                             as page_view_sessions,
        sum(reached_cart)                                                  as cart_sessions,
        sum(reached_purchase)                                              as purchase_sessions,
        round(sum(reached_cart)     * 100.0 / nullif(sum(reached_page_view), 0), 1) as view_to_cart_pct,
        round(sum(reached_purchase) * 100.0 / nullif(sum(reached_cart), 0), 1)      as cart_to_purchase_pct,
        round(sum(reached_purchase) * 100.0 / nullif(sum(reached_page_view), 0), 1) as overall_cvr_pct
    from funnel_events
    group by channel_group
)

select *
from funnel_summary
order by overall_cvr_pct desc
