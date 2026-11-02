{# What the site shows: currently active tech roles, per role, overall (all_tech)
   and for entry-level titles (entry_level). pct_of_companies is the guard against
   big boards: Anduril alone is ~19% of all postings, but only one company. #}

with active as (
    select unique_role_key, company_token, role, is_entry_level
    from {{ ref('fct_postings') }}
    where is_active and is_tech_role
),

active_all as (
    select distinct unique_role_key, company_token, role from active
    union all
    select distinct unique_role_key, company_token, 'all_tech' from active
    union all
    select distinct unique_role_key, company_token, 'entry_level' from active where is_entry_level
),

totals as (
    select role, count(distinct unique_role_key) as roles_total, count(distinct company_token) as companies_total
    from active_all
    group by 1
),

mentions as (
    select distinct m.unique_role_key, m.company_token, a.role, m.skill, m.category
    from {{ ref('fct_skill_mentions') }} as m
    join active_all as a on a.unique_role_key = m.unique_role_key
    join {{ ref('fct_postings') }} as p on p.posting_key = m.posting_key and p.is_active
)

select
    m.role,
    m.skill,
    m.category,
    count(distinct m.unique_role_key) as roles_mentioning,
    t.roles_total,
    round(100.0 * count(distinct m.unique_role_key) / t.roles_total, 1) as pct_of_roles,
    count(distinct m.company_token) as companies_mentioning,
    t.companies_total,
    round(100.0 * count(distinct m.company_token) / t.companies_total, 1) as pct_of_companies
from mentions as m
join totals as t on t.role = m.role
group by m.role, m.skill, m.category, t.roles_total, t.companies_total
