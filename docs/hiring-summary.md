# Hiring Summary — E-commerce Analytics Engineering

## One-line summary

Analytics engineering case study: dbt + DuckDB/BigQuery pipeline transforming raw e-commerce events and orders into BI-ready mart tables, with full data quality tests, SQL analysis queries, and cross-adapter compatibility.

## What this project demonstrates

| Skill | Evidence |
|-------|----------|
| **dbt modeling** | 3-layer architecture: staging (4 models) → intermediate (2) → marts (4) |
| **SQL analytics** | 3 analysis queries: channel performance, conversion funnel, product revenue |
| **Data quality** | 40+ dbt tests across all layers: not_null, unique, accepted_values, relationships |
| **Cross-adapter SQL** | Models run on DuckDB (CI/local) and BigQuery (production) using Jinja adapter dispatch |
| **Business framing** | Channel grouping macro, funnel analysis, return rate tracking, revenue attribution |
| **Data documentation** | Every mart column has a business description in schema YML |
| **CI** | GitHub Actions: dbt seed + run + test on every push |

## Data model overview

### Sources (raw)
- `events` — website clickstream: page_view, cart, purchase, cancel
- `order_items` — transactional order line items with status and pricing
- `products` — product catalog with cost and retail price
- `users` — user profiles with demographics and signup attribution

### Mart outputs
- `fct_order_marketing` — revenue, returns, and channel attribution per order item
- `fct_marketing_web_performance` — session-level conversion and engagement metrics
- `dim_user` — user demographics with age segmentation and channel groups
- `dim_products` — product catalog with computed margin metrics

## Key business questions answered

1. Which marketing channels drive the most revenue and conversions?
2. Where do users drop off in the purchase funnel (page_view → cart → purchase)?
3. Which products have the highest return rates and what is their net revenue contribution?

## Interview-ready talking points

1. The 3-layer dbt architecture (staging → intermediate → marts) separates source cleaning, business logic, and reporting surfaces so each layer is independently testable.
2. Traffic attribution in `int_orders_enriched` uses a window function to find the nearest purchase event for each order, with fallback to signup source — showing awareness of attribution complexity.
3. The `marketing_channel_group` macro centralizes channel classification logic so any model can group sources without duplicating CASE logic.
4. Cross-adapter Jinja blocks (`{% if target.type == 'bigquery' %}`) let the project run in CI with DuckDB seeds and in production with BigQuery, demonstrating multi-environment awareness.
5. 40+ data quality tests enforce contracts at every layer — not just at the mart level.
