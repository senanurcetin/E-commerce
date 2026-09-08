-- Direct identifiers are deliberately not published here. Names, raw email
-- addresses and street addresses carry no analytical value for the dashboards
-- built on this mart, which group by age, gender, country and channel. Email is
-- reduced to a hash plus its domain, and coordinates are rounded. Anything that
-- genuinely needs the raw values reads stg_users under its own access control.

with users as (
    select * from {{ ref('stg_users') }}
),
final as (
    select
        user_id,
        {% if target.type == 'bigquery' %}
        to_hex(sha256(lower(trim(email)))) as user_email_hash,
        coalesce(nullif(split(email, '@')[safe_offset(1)], ''), 'unknown') as email_domain,
        {% else %}
        sha256(lower(trim(email))) as user_email_hash,
        coalesce(nullif(split_part(email, '@', 2), ''), 'unknown') as email_domain,
        {% endif %}
        age, gender,
        city, state, country, postal_code,
        -- One decimal is roughly 11 km: regional analysis still works, the point
        -- no longer identifies a household.
        round(latitude, 1) as latitude_approx,
        round(longitude, 1) as longitude_approx,
        signup_traffic_source, user_created_at,
        {% if target.type == 'bigquery' %}
        datetime(user_created_at, "Europe/Istanbul") as user_created_at_local,
        {% else %}
        user_created_at as user_created_at_local,
        {% endif %}
        case
            when age is null then 'unknown'
            when age < 25 then '18-24'
            when age between 25 and 34 then '25-34'
            when age between 35 and 44 then '35-44'
            else '45+'
        end as age_segment,
        {{ marketing_channel_group('signup_traffic_source') }} as signup_channel_group
    from users
)
select * from final
