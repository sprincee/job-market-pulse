-- Fails if the newest day has few companies: a partial ingest shouldn't reach
-- the site, and the date would otherwise never be reprocessed.
select snapshot_date, count(distinct company_token) as companies
from {{ ref('stg_postings_daily') }}
where snapshot_date = (select max(snapshot_date) from {{ ref('stg_postings_daily') }})
group by 1
having count(distinct company_token) < 30
