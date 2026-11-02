{# All three sources in one shape, for raw days not loaded yet. Only .json.gz is
   read: laptop-era plain .json files have .json.gz twins from the S3 sync.
   A view, so the bulky raw text is never stored here. #}
{{ config(materialized='view') }}

{% set raw = var('raw_path') %}
{% set since = last_loaded_date() %}
{% set token = "regexp_extract(filename, '([^/\\\\]+)\\.json\\.gz$', 1)" %}

select
    'greenhouse' as source,
    {{ token }} as company_token,
    cast(date as date) as snapshot_date,
    id as posting_id,
    trim(title) as title,
    location.name as location,
    cast(null as varchar) as workplace_type,
    absolute_url as url,
    try_cast(first_published as timestamp) as published_at,
    departments[1].name as department,
    content as body_raw
from read_json(
    '{{ raw }}/source=greenhouse/date=*/*.json.gz',
    format = 'array', filename = true, hive_partitioning = true,
    columns = {
        'id': 'VARCHAR', 'title': 'VARCHAR', 'location': 'STRUCT(name VARCHAR)',
        'absolute_url': 'VARCHAR', 'first_published': 'VARCHAR',
        'departments': 'STRUCT(name VARCHAR)[]', 'content': 'VARCHAR'
    }
)
where date > {{ since }}

union all

select
    'lever',
    {{ token }},
    cast(date as date),
    id,
    trim(text),
    categories.location,
    lower(workplaceType),
    hostedUrl,
    epoch_ms(createdAt),
    categories.team,
    -- additionalPlain is left out: like Greenhouse's closing section, it's mostly company boilerplate
    concat_ws(' ', descriptionPlain,
        array_to_string(list_transform(lists, lambda x: concat_ws(' ', x.text, x.content)), ' '))
from read_json(
    '{{ raw }}/source=lever/date=*/*.json.gz',
    format = 'array', filename = true, hive_partitioning = true,
    columns = {
        'id': 'VARCHAR', 'text': 'VARCHAR',
        'categories': 'STRUCT(location VARCHAR, team VARCHAR)',
        'workplaceType': 'VARCHAR', 'hostedUrl': 'VARCHAR', 'createdAt': 'BIGINT',
        'descriptionPlain': 'VARCHAR', 'lists': 'STRUCT(text VARCHAR, content VARCHAR)[]'
    }
)
where date > {{ since }}

union all

select
    'ashby',
    {{ token }},
    cast(date as date),
    id,
    trim(title),
    location,
    -- workplaceType first: isRemote is also true for many hybrid roles
    coalesce(lower(workplaceType), case when isRemote then 'remote' end),
    jobUrl,
    try_cast(publishedAt as timestamp),
    department,
    descriptionPlain
from read_json(
    '{{ raw }}/source=ashby/date=*/*.json.gz',
    format = 'array', filename = true, hive_partitioning = true,
    columns = {
        'id': 'VARCHAR', 'title': 'VARCHAR', 'location': 'VARCHAR',
        'isRemote': 'BOOLEAN', 'workplaceType': 'VARCHAR', 'jobUrl': 'VARCHAR',
        'publishedAt': 'VARCHAR', 'department': 'VARCHAR', 'descriptionPlain': 'VARCHAR'
    }
)
where date > {{ since }}
