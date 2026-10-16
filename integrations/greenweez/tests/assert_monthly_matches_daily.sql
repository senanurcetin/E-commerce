-- Every monthly figure must equal the sum of its days; the weighted monthly
-- average basket must equal revenue / transactions. Returns offending months.
with daily as (
    select
        {{ month_start('date') }} as datemonth,
        sum(ads_cost) as ads_cost,
        sum(operational_margin) as operational_margin,
        sum(transactions) as transactions
    from {{ ref('finance_campaigns_day') }}
    group by 1
)

select m.datemonth
from {{ ref('finance_campaigns_month') }} as m
inner join daily as d
    on m.datemonth = d.datemonth
where
    abs(m.ads_cost - d.ads_cost) > 0.5
    or abs(m.operational_margin - d.operational_margin) > 0.5
    or m.transactions != d.transactions
    or abs(m.average_basket - m.revenue / m.transactions) > 0.01
