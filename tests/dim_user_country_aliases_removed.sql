select *
from {{ ref('dim_user') }}
where lower(country) in ('españa', 'brasil', 'deutschland')
