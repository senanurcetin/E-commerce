{#
    Shared staging logic for the ad-platform raw tables (adwords, bing, criteo,
    facebook): they all expose the same columns, only the source table differs.
#}
{% macro stg_ads_source(source_table) -%}
select
    cast(date_date as date) as date_date,
    cast(paid_source as {{ dbt.type_string() }}) as paid_source,
    cast(campaign_key as {{ dbt.type_string() }}) as campaign_key,
    cast(camPGN_name as {{ dbt.type_string() }}) as campaign_name,
    cast(ads_cost as {{ dbt.type_numeric() }}) as ads_cost,
    cast(impression as {{ dbt.type_int() }}) as impression,
    cast(click as {{ dbt.type_int() }}) as click
from {{ source('raw', source_table) }}
{%- endmacro %}
