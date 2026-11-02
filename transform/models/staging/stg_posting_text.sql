{# One row per posting: its latest cleaned description. Text is stored once per
   posting rather than once per day, and rewritten only when it changes, which
   is what keeps the DuckDB file small. #}
{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='posting_key') }}

with latest as (
    select
        concat_ws('|', source, company_token, posting_id) as posting_key,
        snapshot_date,
        md5(coalesce(body_raw, '')) as body_hash,
        body_raw
    from {{ ref('base_raw_new') }}
    qualify row_number() over (
        partition by source, company_token, posting_id
        order by snapshot_date desc
    ) = 1
)

select
    latest.posting_key,
    latest.snapshot_date as text_as_of,
    latest.body_hash,
    {{ clean_html('latest.body_raw') }} as body_text
from latest
{% if is_incremental() %}
left join {{ this }} as existing on existing.posting_key = latest.posting_key
where existing.body_hash is distinct from latest.body_hash
{% endif %}
