with source as (

    select *
    from {{ source('e_ticaret_raw', 'users') }}

),

renamed as (

    select
        cast(id as int64) as user_id,

        coalesce(nullif(trim(first_name), ''), 'unknown') as first_name,
        coalesce(nullif(trim(last_name), ''), 'unknown') as last_name,
        coalesce(nullif(trim(email), ''), 'unknown') as email,

        cast(age as int64) as age,
        coalesce(lower(nullif(trim(gender), '')), 'unknown') as gender,

        coalesce(nullif(trim(city), ''), 'unknown') as city,
        coalesce(nullif(trim(state), ''), 'unknown') as state,
        {{ normalize_country("nullif(trim(country), '')") }} as country,
        coalesce(nullif(trim(postal_code), ''), 'unknown') as postal_code,
        coalesce(nullif(trim(street_address), ''), 'unknown') as street_address,

        cast(latitude as numeric) as latitude,
        cast(longitude as numeric) as longitude,

        coalesce(lower(nullif(trim(traffic_source), '')), 'unknown') as signup_traffic_source,
        cast(created_at as timestamp) as user_created_at

    from source
    where id is not null

)

select
    user_id,
    first_name,
    last_name,
    email,
    age,
    gender,
    city,
    state,
    country,
    postal_code,
    street_address,
    latitude,
    longitude,
    signup_traffic_source,
    user_created_at
from renamed
