{{ config(materialized='view') }}

-- full outer join: ad spend on days without any order must not disappear.
select
    coalesce(fd.date_date, icd.date_date) as date,
    round(coalesce(fd.operational_margin, 0) - coalesce(icd.ads_cost, 0), 2) as ads_margin,
    round(fd.avg_basket, 2) as average_basket,
    round(coalesce(fd.operational_margin, 0), 2) as operational_margin,
    round(coalesce(icd.ads_cost, 0), 2) as ads_cost,
    coalesce(icd.ads_impression, 0) as ads_impression,
    coalesce(icd.ads_clicks, 0) as ads_clicks,
    coalesce(fd.total_transactions, 0) as transactions,
    coalesce(fd.total_quantity, 0) as quantity,
    round(coalesce(fd.total_revenue, 0), 2) as revenue,
    round(coalesce(fd.total_purchase_cost, 0), 2) as purchase_cost,
    round(coalesce(fd.total_margin, 0), 2) as margin,
    round(coalesce(fd.total_shipping_fee, 0), 2) as shipping_fee,
    round(coalesce(fd.total_log_cost, 0), 2) as log_cost,
    round(coalesce(fd.total_ship_cost, 0), 2) as ship_cost
from {{ ref('finance_days') }} as fd
full outer join {{ ref('int_campaigns_day') }} as icd
    on fd.date_date = icd.date_date
