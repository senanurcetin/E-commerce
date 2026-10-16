{% set ad_sources = ['adwords', 'bing', 'criteo', 'facebook'] %}

{% for ad_source in ad_sources %}
    select
        date_date,
        paid_source,
        campaign_key,
        campaign_name,
        ads_cost,
        impression,
        click
    from {{ ref('stg_raw__' ~ ad_source) }}
    {% if not loop.last %}
        union all
    {% endif %}
{% endfor %}
