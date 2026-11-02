-- Fails if a posting appears twice on one day, which would double-count it.
select posting_key, snapshot_date, count(*) as n
from {{ ref('stg_postings_daily') }}
group by 1, 2
having count(*) > 1
