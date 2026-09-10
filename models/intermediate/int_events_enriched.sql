-- User attributes are joined in the marts layer against dim_user rather than
-- here. Joining them at event grain widened the largest table in the project
-- with columns nothing downstream read, and pulled names, email, and other
-- direct identifiers into a view that anyone with dataset access could query.

with events as (

    select *
    from {{ ref('stg_events') }}

),

final as (

    select
        event_id,
        user_id,
        session_id,
        sequence_number,
        event_created_at,
        ip_address,
        city,
        state,
        postal_code,
        browser,
        traffic_source,
        page_uri,
        event_type_raw,
        event_type

    from events

)

select *
from final
