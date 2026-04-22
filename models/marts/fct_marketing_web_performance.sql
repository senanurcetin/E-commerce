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
        datetime(min(event_created_at), "Europe/Istanbul") as session_start_at_local,
        datetime(max(event_created_at), "Europe/Istanbul") as session_end_at_local,
        date(datetime(min(event_created_at), "Europe/Istanbul")) as session_date,
        extract(hour from datetime(min(event_created_at), "Europe/Istanbul")) as session_hour,
        timestamp_diff(max(event_created_at), min(event_created_at), second) as session_duration_seconds,
        count(*) as total_events,
        countif(event_type = 'page_view') as page_view_events,
        countif(event_type = 'purchase') as purchase_events,
        countif(event_type = 'cancel') as cancel_events,
        max(case when event_type = 'page_view' then 1 else 0 end) as has_page_view,
        max(case when event_type = 'purchase' then 1 else 0 end) as has_purchase,
        max(case when event_type = 'cancel' then 1 else 0 end) as has_cancel,
        any_value(traffic_source) as traffic_source,
        any_value(browser) as browser
    from events
    group by session_id, user_id

),

users as (

    select *
    from {{ ref('dim_user') }}

),

final as (

    select
        s.session_id,
        s.user_id,
        s.session_start_at,
        s.session_end_at,
        s.session_start_at_local,
        s.session_end_at_local,
        s.session_date,
        s.session_hour,
        s.session_duration_seconds,
        s.total_events,
        s.page_view_events,
        s.purchase_events,
        s.cancel_events,
        s.has_page_view,
        s.has_purchase,
        s.has_cancel,
        s.traffic_source,
        s.browser,

        u.age_segment,
        u.gender,
        u.country,
        u.state,
        u.city,
        u.signup_traffic_source

    from sessions s
    left join users u
        on s.user_id = u.user_id

)

select *
from final