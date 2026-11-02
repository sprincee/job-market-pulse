{# One row per posting per day it was listed; each run appends only new days.
   Holds a hash of the description rather than its text, so this stays small
   even after years of history. Source for first seen, last seen and trends. #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select
    concat_ws('|', source, company_token, posting_id) as posting_key,
    source,
    company_token,
    posting_id,
    snapshot_date,
    title,
    location,
    workplace_type,
    url,
    published_at,
    department,
    md5(coalesce(body_raw, '')) as body_hash
from {{ ref('base_raw_new') }}
