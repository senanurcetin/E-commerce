-- Monthly ad efficiency per paid source. Only platform-native metrics are used
-- (cost, impressions, clicks), so there is no ROAS here: revenue cannot be
-- attributed to a source with the data available. Ratios are ratios of sums.
with monthly as (
    select
        {{ month_start('date_date') }} as datemonth,
        paid_source,
        sum(ads_cost) as ads_cost,
        sum(impression) as impressions,
        sum(click) as clicks
    from {{ ref('int_campaigns') }}
    group by datemonth, paid_source
)

select
    datemonth,
    paid_source,
    round(ads_cost, 2) as ads_cost,
    impressions,
    clicks,
    round({{ dbt_utils.safe_divide('ads_cost', 'clicks') }}, 2) as cpc,
    round({{ dbt_utils.safe_divide('clicks', 'impressions') }}, 4) as ctr,
    round({{ dbt_utils.safe_divide('ads_cost', 'sum(ads_cost) over (partition by datemonth)') }}, 4) as spend_share
from monthly
