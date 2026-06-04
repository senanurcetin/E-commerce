{% macro normalize_country(source_expression) -%}
    case
        {% if target.type == 'bigquery' %}
        when regexp_contains(lower(trim(coalesce({{ source_expression }}, 'unknown'))), r'^espa') then 'Spain'
        {% else %}
        when lower(trim(coalesce({{ source_expression }}, 'unknown'))) like 'espa%' then 'Spain'
        {% endif %}
        when lower(trim(coalesce({{ source_expression }}, 'unknown'))) = 'brasil' then 'Brazil'
        when lower(trim(coalesce({{ source_expression }}, 'unknown'))) = 'deutschland' then 'Germany'
        when lower(trim(coalesce({{ source_expression }}, 'unknown'))) = 'unknown' then 'unknown'
        else trim(coalesce({{ source_expression }}, 'unknown'))
    end
{%- endmacro %}
