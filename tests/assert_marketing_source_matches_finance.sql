-- Per-source figures must add up to the blended monthly totals.
with source_totals as (
    select
        datemonth,
        sum(ads_cost) as ads_cost,
        sum(impressions) as impressions,
        sum(clicks) as clicks
    from {{ ref('marketing_source_month') }}
    group by datemonth
)

select s.datemonth
from source_totals as s
inner join {{ ref('marketing_performance_month') }} as m
    on s.datemonth = m.datemonth
where
    abs(s.ads_cost - m.ads_cost) > 0.5
    or s.impressions != m.ads_impression
    or s.clicks != m.ads_clicks
