with events as (
    select * from {{ ref('stg_events') }}
),

users as (
    select * from {{ ref('stg_users') }}
),

joined as (
    select
        e.event_id,
        e.user_id,
        e.session_id,
        e.event_created_at,
        e.event_type,
        e.page_uri,
        e.traffic_source as event_source,

        u.country,
        u.gender,
        u.age,
        u.traffic_source as user_acquisition_source
    from events e
    left join users u
        on e.user_id = u.user_id
)

select * from joined