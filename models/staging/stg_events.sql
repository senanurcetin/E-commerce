with source as (

    select *
    from {{ source('e_ticaret_raw', 'events') }}

),

renamed as (

    select
        cast(id as int64) as event_id,
        cast(user_id as int64) as user_id,
        cast(sequence_number as int64) as sequence_number,
        cast(session_id as string) as session_id,
        cast(created_at as timestamp) as event_created_at,
        cast(ip_address as string) as ip_address,
        trim(city) as city,
        trim(state) as state,
        trim(postal_code) as postal_code,
        lower(trim(browser)) as browser,
        lower(trim(traffic_source)) as traffic_source,
        trim(uri) as page_uri,
        lower(trim(event_type)) as event_type
    from source

)

select *
from renamed