{{ config(
    materialized='table',
    partition_by={
        "field": "session_date",
        "data_type": "date"
    },
    cluster_by=['channel_group', 'traffic_source', 'user_id']
) }}

with events as (

    select *
    from {{ ref('int_events_enriched') }}
    where session_id is not null

),

sessions as (

    select
        concat(
            cast(session_id as string),
            '-',
            coalesce(cast(user_id as string), 'anonymous')
        ) as session_sk,

        session_id,
        user_id,

        min(event_created_at) as session_start_at,
        max(event_created_at) as session_end_at,

        datetime(min(event_created_at), "Europe/Istanbul") as session_start_at_local,
        datetime(max(event_created_at), "Europe/Istanbul") as session_end_at_local,
        date(datetime(min(event_created_at), "Europe/Istanbul")) as session_date,
        extract(hour from datetime(min(event_created_at), "Europe/Istanbul")) as session_hour,

        timestamp_diff(max(event_created_at), min(event_created_at), second) as session_duration_seconds,
        round(timestamp_diff(max(event_created_at), min(event_created_at), second) / 60.0, 2) as session_duration_minutes,

        count(*) as total_events,
        countif(lower(event_type) = 'page_view') as page_view_events,
        countif(lower(event_type) = 'purchase') as purchase_events,
        countif(lower(event_type) = 'cancel') as cancel_events,

        max(case when lower(event_type) = 'page_view' then 1 else 0 end) as has_page_view,
        max(case when lower(event_type) = 'purchase' then 1 else 0 end) as has_purchase,
        max(case when lower(event_type) = 'cancel' then 1 else 0 end) as has_cancel,

        array_agg(traffic_source ignore nulls order by sequence_number, event_created_at limit 1)[safe_offset(0)] as traffic_source,
        array_agg(browser ignore nulls order by sequence_number, event_created_at limit 1)[safe_offset(0)] as browser

    from events
    group by session_id, user_id

),

users as (

    select *
    from {{ ref('dim_user') }}

),

final as (

    select
        s.session_sk,
        s.session_id,
        s.user_id,

        s.session_start_at,
        s.session_end_at,
        s.session_start_at_local,
        s.session_end_at_local,
        s.session_date,
        s.session_hour,

        s.session_duration_seconds,
        s.session_duration_minutes,
        s.total_events,
        s.page_view_events,
        s.purchase_events,
        s.cancel_events,
        s.has_page_view,
        s.has_purchase,
        s.has_cancel,

        case when s.has_purchase = 1 then 1 else 0 end as is_converted,

        coalesce(s.traffic_source, 'unknown') as traffic_source,

        {{ marketing_channel_group('s.traffic_source') }} as channel_group,

        coalesce(s.browser, 'unknown') as browser,

        u.age_segment,
        u.gender,
        u.country,
        u.state,
        u.city,
        u.signup_traffic_source,
        u.signup_channel_group

    from sessions s
    left join users u
        on s.user_id = u.user_id

)

select *
from final
