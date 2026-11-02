{# One row per tech posting and skill it mentions. Rebuilt from text already in
   the warehouse, so dictionary changes apply to all history. #}

select
    p.posting_key,
    p.unique_role_key,
    p.company_token,
    p.role,
    s.skill,
    s.category
from {{ ref('fct_postings') }} as p
join {{ ref('stg_posting_text') }} as t on t.posting_key = p.posting_key
join {{ ref('skills') }} as s
    on regexp_matches(p.title || ' ' || t.body_text, s.pattern)
    -- a company naming its own product isn't demand for that skill
    and (s.vendor_token is null or s.vendor_token <> p.company_token)
where p.is_tech_role
