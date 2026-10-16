-- Spend shares of all sources in a month must add up to 1.
select datemonth
from {{ ref('marketing_source_month') }}
group by datemonth
having abs(sum(spend_share) - 1) > 0.001
