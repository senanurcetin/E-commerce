with validation as (

    select
        sum(page_view_events) as total_page_view_events
    from {{ ref('fct_marketing_web_performance') }}

)

select *
from validation
where total_page_view_events = 0
