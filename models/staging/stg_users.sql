with source as (

    select *
    from {{ source('e_ticaret_raw', 'users') }}

),

renamed as (

    select
        cast(id as int64) as user_id,
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        lower(trim(email)) as email,
        cast(age as int64) as age,
        upper(trim(gender)) as gender,
        trim(state) as state,
        trim(street_address) as street_address,
        trim(postal_code) as postal_code,
        trim(city) as city,
        trim(country) as country,
        cast(latitude as float64) as latitude,
        cast(longitude as float64) as longitude,
        lower(trim(traffic_source)) as traffic_source,
        cast(created_at as timestamp) as user_created_at,
        st_astext(user_geom) as user_geom_wkt
    from source

)

select *
from renamed