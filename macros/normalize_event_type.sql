{% macro normalize_event_type(source_expression) -%}
    case
        when lower(coalesce({{ source_expression }}, 'unknown')) in ('home', 'product', 'department') then 'page_view'
        when lower(coalesce({{ source_expression }}, 'unknown')) in ('cart', 'purchase', 'cancel') then lower(coalesce({{ source_expression }}, 'unknown'))
        else 'unknown'
    end
{%- endmacro %}
