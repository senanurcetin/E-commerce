with source as (

    select *
    from {{ source('e_ticaret_raw', 'events') }}

),

cleaned as (

    select
        cast(id as int64) as event_id,
        cast(user_id as int64) as user_id,
        cast(sequence_number as int64) as sequence_number,
        cast(session_id as string) as session_id,
        cast(created_at as timestamp) as event_created_at,
        cast(ip_address as string) as ip_address,

        coalesce(nullif(trim(city), ''), 'unknown') as city,
        coalesce(nullif(trim(state), ''), 'unknown') as state,
        coalesce(nullif(trim(postal_code), ''), 'unknown') as postal_code,

        coalesce(lower(nullif(trim(browser), '')), 'unknown') as browser,
        coalesce(lower(nullif(trim(traffic_source), '')), 'unknown') as traffic_source,
        coalesce(nullif(trim(uri), ''), 'unknown') as page_uri,
        coalesce(lower(nullif(trim(event_type), '')), 'unknown') as event_type_raw

    from source
    where id is not null

),

renamed as (

    select
        event_id,
        user_id,
        sequence_number,
        session_id,
        event_created_at,
        ip_address,
        city,
        state,
        postal_code,
        browser,
        traffic_source,
        page_uri,
        event_type_raw,
        {{ normalize_event_type('event_type_raw') }} as event_type

    from cleaned

)

select
    event_id,
    user_id,
    sequence_number,
    session_id,
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
from renamed
