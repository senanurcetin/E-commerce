-- Blended monthly marketing efficiency. Revenue is not attributed to a source or
-- campaign, so ROAS only exists at this blended level. All ratios are ratios of
-- sums (never an average of daily ratios); a zero denominator gives NULL.
select
    datemonth,
    revenue,
    operational_margin,
    ads_cost,
    ads_impression,
    ads_clicks,
    transactions,
    round({{ dbt_utils.safe_divide('revenue', 'ads_cost') }}, 2) as roas,
    round({{ dbt_utils.safe_divide('operational_margin', 'ads_cost') }}, 2) as margin_roas,
    round({{ dbt_utils.safe_divide('ads_cost', 'ads_clicks') }}, 2) as cpc,
    round({{ dbt_utils.safe_divide('ads_clicks', 'ads_impression') }}, 4) as ctr
from {{ ref('finance_campaigns_month') }}
