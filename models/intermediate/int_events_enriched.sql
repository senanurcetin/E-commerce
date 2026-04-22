with events as (

    select *
    from {{ ref('stg_events') }}

),

users as (

    select *
    from {{ ref('stg_users') }}

),

final as (

    select
        e.event_id,
        e.user_id,
        e.session_id,
        e.sequence_number,
        e.event_created_at,
        e.ip_address,
        e.city,
        e.state,
        e.postal_code,
        e.browser,
        e.traffic_source,
        e.page_uri,
        e.event_type,

        u.first_name,
        u.last_name,
        u.email,
        u.age,
        u.gender,
        u.country,
        u.signup_traffic_source,
        u.user_created_at

    from events e
    left join users u
        on e.user_id = u.user_id

)

select *
from final