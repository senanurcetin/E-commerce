with users as (

    select *
    from {{ ref('stg_users') }}

),

final as (

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
        user_created_at,
        datetime(user_created_at, "Europe/Istanbul") as user_created_at_local,

        case
            when age is null then 'unknown'
            when age < 25 then '18-24'
            when age between 25 and 34 then '25-34'
            when age between 35 and 44 then '35-44'
            else '45+'
        end as age_segment,

        case
            when signup_traffic_source in ('facebook', 'youtube', 'adwords', 'display') then 'paid'
            when signup_traffic_source in ('email') then 'owned'
            when signup_traffic_source in ('search', 'organic') then 'organic'
            else 'other'
        end as signup_channel_group

    from users

)

select *
from final