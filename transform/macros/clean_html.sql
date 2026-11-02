{# HTML to plain text. Greenhouse escapes its HTML, so decode first; only then
   are its intro, closing and pay sections visible to remove. Those sections
   describe the company or offer, not what the job requires. #}
{% macro clean_html(col) %}
trim(regexp_replace(
  replace(regexp_replace(
    replace(replace(replace(replace(replace(
      regexp_replace(
        regexp_replace(
          replace(replace(replace(replace(replace({{ col }},
            '&lt;', '<'), '&gt;', '>'), '&quot;', '"'), '&#39;', ''''), '&amp;', '&'),
          '(?s)<div class="content-(intro|conclusion|pay-transparency)">.*?</div>', ' ', 'g'),
        '<[^>]+>', ' ', 'g'),
      '&amp;', '&'), '&lt;', '<'), '&gt;', '>'), '&quot;', '"'), '&#39;', ''''),
    '&#?[a-zA-Z0-9]+;', ' ', 'g'), chr(160), ' '),
  '\s+', ' ', 'g'))
{% endmacro %}
