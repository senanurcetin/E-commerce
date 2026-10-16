{% if var('source_system', 'gwz_raw') == 'fvt_gsheet' %}
-- fvt_gsheet: only a daily total ad cost exists; impressions and clicks are unknown (NULL),
-- so CPC and CTR come out NULL downstream while blended ROAS still works.
select
    date_date,
    sum(ads_cost) as ads_cost,
    cast(null as {{ dbt.type_int() }}) as ads_impression,
    cast(null as {{ dbt.type_int() }}) as ads_clicks
from {{ ref('stg_gsheet__campaign') }}
group by date_date
{% else %}
    select
        date_date,
        sum(ads_cost) as ads_cost,
        sum(impression) as ads_impression,
        sum(click) as ads_clicks
    from {{ ref('int_campaigns') }}
    group by date_date
{% endif %}
