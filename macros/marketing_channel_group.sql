{% macro marketing_channel_group(source_expression) -%}
    case
        when lower(coalesce({{ source_expression }}, 'unknown')) in ('facebook', 'youtube', 'adwords', 'display') then 'paid'
        when lower(coalesce({{ source_expression }}, 'unknown')) = 'email' then 'owned'
        when lower(coalesce({{ source_expression }}, 'unknown')) in ('search', 'organic') then 'organic'
        else 'other'
    end
{%- endmacro %}
