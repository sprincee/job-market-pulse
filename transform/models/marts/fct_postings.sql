{# One row per posting, with its role and first and last seen dates. Rebuilt each
   run from data already in the warehouse, so rule changes apply to all history
   and no raw data is read. #}

with postings as (
    select
        posting_key,
        any_value(source) as source,
        any_value(company_token) as company_token,
        min(snapshot_date) as first_seen,
        max(snapshot_date) as last_seen,
        arg_max(title, snapshot_date) as title,
        arg_max(location, snapshot_date) as location,
        arg_max(workplace_type, snapshot_date) as workplace_type,
        arg_max(url, snapshot_date) as url,
        arg_max(department, snapshot_date) as department
    from {{ ref('stg_postings_daily') }}
    group by 1
),

excluded as (
    select distinct p.title
    from (select distinct title from postings) as p
    join {{ ref('title_excludes') }} as e on regexp_matches(p.title, e.pattern)
),

title_roles as (
    select p.title, r.role
    from (select distinct title from postings) as p
    join {{ ref('role_rules') }} as r on regexp_matches(p.title, r.pattern)
    where p.title not in (select title from excluded)
    qualify row_number() over (partition by p.title order by r.role_order) = 1
),

entry_level_titles as (
    select p.title
    from (select distinct title from postings) as p
    join {{ ref('entry_level_rules') }} as e on regexp_matches(p.title, e.pattern)
    group by p.title
    having count(*) filter (where e.kind = 'include') > 0
       and count(*) filter (where e.kind = 'exclude') = 0
)

select
    p.posting_key,
    p.source,
    p.company_token,
    p.title,
    coalesce(r.role, 'other') as role,
    r.role is not null as is_tech_role,
    r.role is not null and p.title in (select title from entry_level_titles) as is_entry_level,
    -- one job listed in many cities counts once
    p.company_token || '|' || lower(p.title) as unique_role_key,
    p.location,
    case
        when p.workplace_type in ('remote', 'hybrid', 'onsite') then p.workplace_type
        when p.location ilike '%remote%' then 'remote'
        when p.location ilike '%hybrid%' then 'hybrid'
        else 'unknown'
    end as work_mode,
    p.url,
    p.department,
    p.first_seen,
    p.last_seen,
    p.last_seen = (select max(last_seen) from postings) as is_active,
    -- a posting isn't new if it was there the day we started tracking its company
    p.first_seen > c.first_snapshot_date as is_new_since_tracking_began
from postings as p
left join title_roles as r on r.title = p.title
left join {{ ref('dim_company') }} as c on c.company_token = p.company_token
