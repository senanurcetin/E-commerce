select *
from {{ ref('fct_marketing_web_performance') }}
where session_duration_seconds < 0