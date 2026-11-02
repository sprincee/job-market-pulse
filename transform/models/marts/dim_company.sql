select
    c.company_token,
    c.company_name,
    c.ats,
    min(d.snapshot_date) as first_snapshot_date,
    max(d.snapshot_date) as last_snapshot_date
from {{ ref('companies') }} as c
left join {{ ref('stg_postings_daily') }} as d on d.company_token = c.company_token
group by 1, 2, 3
