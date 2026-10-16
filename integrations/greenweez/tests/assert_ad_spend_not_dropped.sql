-- Ad spend on days without orders must survive into the daily mart.
with totals as (
    select
        (select sum(ads_cost) from {{ ref('int_campaigns_day') }}) as source_ads_cost,
        (select sum(ads_cost) from {{ ref('finance_campaigns_day') }}) as mart_ads_cost
)

select *
from totals
where abs(source_ads_cost - mart_ads_cost) > 0.5
