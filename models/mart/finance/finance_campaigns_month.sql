-- average_basket is weighted (revenue / transactions), not an average of daily averages.
select
    {{ month_start('date') }} as datemonth,
    round(sum(ads_margin), 2) as ads_margin,
    round({{ dbt_utils.safe_divide('sum(revenue)', 'sum(transactions)') }}, 2) as average_basket,
    round(sum(operational_margin), 2) as operational_margin,
    round(sum(ads_cost), 2) as ads_cost,
    sum(ads_impression) as ads_impression,
    sum(ads_clicks) as ads_clicks,
    sum(transactions) as transactions,
    sum(quantity) as quantity,
    round(sum(revenue), 2) as revenue,
    round(sum(purchase_cost), 2) as purchase_cost,
    round(sum(margin), 2) as margin,
    round(sum(shipping_fee), 2) as shipping_fee,
    round(sum(log_cost), 2) as log_cost,
    round(sum(ship_cost), 2) as ship_cost
from {{ ref('finance_campaigns_day') }}
group by datemonth
