{# Newest snapshot date already in the warehouse, as a SQL date literal.
   Returned as a literal (not a subquery) so DuckDB can skip older raw
   partitions without opening them. A full refresh starts from the beginning. #}
{% macro last_loaded_date() %}
  {% set start = "date '1900-01-01'" %}
  {% if not execute or flags.FULL_REFRESH %}
    {{ return(start) }}
  {% endif %}
  {% set rel = adapter.get_relation(database=target.database, schema=target.schema, identifier='stg_postings_daily') %}
  {% if rel is none %}
    {{ return(start) }}
  {% endif %}
  {% set newest = run_query("select max(snapshot_date) from " ~ rel).columns[0].values()[0] %}
  {{ return("date '" ~ newest ~ "'" if newest else start) }}
{% endmacro %}
