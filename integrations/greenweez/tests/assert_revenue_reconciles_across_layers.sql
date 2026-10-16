{% set staging_model = 'stg_gsheet__orders' if var('source_system', 'gwz_raw') == 'fvt_gsheet' else 'stg_raw__sales' %}

-- Total revenue must be identical in staging, the daily finance mart and the
-- monthly mart. Returns a row (= failure) when any layer drifts.
with totals as (
    select
        (select sum(revenue) from {{ ref(staging_model) }}) as staging_revenue,
        (select sum(total_revenue) from {{ ref('finance_days') }}) as finance_days_revenue,
        (select sum(revenue) from {{ ref('finance_campaigns_day') }}) as campaigns_day_revenue,
        (select sum(revenue) from {{ ref('finance_campaigns_month') }}) as campaigns_month_revenue
)

select *
from totals
where
    abs(staging_revenue - finance_days_revenue) > 0.5
    or abs(staging_revenue - campaigns_day_revenue) > 0.5
    or abs(staging_revenue - campaigns_month_revenue) > 0.5
