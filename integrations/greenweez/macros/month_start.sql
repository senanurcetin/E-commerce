{#
    First day of the month of a DATE expression, returned as a DATE on every
    adapter (dbt's built-in date_trunc returns a TIMESTAMP on BigQuery).
#}
{% macro month_start(date_expr) -%}
    {{ return(adapter.dispatch('month_start', 'dbt_workintech')(date_expr)) }}
{%- endmacro %}

{% macro default__month_start(date_expr) -%}
    cast(date_trunc('month', {{ date_expr }}) as date)
{%- endmacro %}

{% macro bigquery__month_start(date_expr) -%}
    date_trunc({{ date_expr }}, month)
{%- endmacro %}
