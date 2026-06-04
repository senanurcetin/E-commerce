# Hiring Summary — E-commerce Analytics Engineering

## One-line summary

Analytics engineering case study built end-to-end in **dbt Cloud**, warehoused in **BigQuery**, and visualized in **Power BI** — transforming raw e-commerce clickstream events and orders into BI-ready mart tables with full data quality tests, SQL analysis queries, and cross-adapter CI.

## Actual workflow

```
dbt Cloud IDE  →  BigQuery (warehouse)  →  Power BI (dashboards)
```

Models were authored in the dbt Cloud browser IDE, run against a BigQuery dataset, and the mart outputs were connected to Power BI for channel performance, funnel, and product revenue reporting. This repo versions all SQL and YAML and replays the same pipeline on DuckDB for CI.

## What this project demonstrates

| Skill | Evidence |
|-------|----------|
| **dbt Cloud** | Models authored and run in dbt Cloud IDE against BigQuery |
| **BigQuery** | Production warehouse with partitioned + clustered mart tables |
| **Power BI** | Dashboard layer consuming mart outputs |
| **dbt modeling** | 3-layer architecture: staging (4 models) → intermediate (2) → marts (4) |
| **SQL analytics** | 3 analysis queries: channel performance, conversion funnel, product revenue |
| **Data quality** | 73 dbt tests across all layers: not_null, unique, accepted_values, relationships |
| **Cross-adapter SQL** | Same models run on DuckDB (CI) and BigQuery (prod) via Jinja adapter dispatch |
| **Business framing** | Channel grouping macro, funnel analysis, return rate tracking, revenue attribution |
| **Data documentation** | Every mart column has a business description in schema YML |
| **CI** | GitHub Actions: dbt seed + run + test (57 tests) on every push |

## Data model overview

### Sources (raw BigQuery tables)
- `events` — website clickstream: page_view, cart, purchase, cancel
- `order_items` — transactional order line items with status and pricing
- `products` — product catalog with cost and retail price
- `users` — user profiles with demographics and signup attribution

### Mart outputs (Power BI datasets)
- `fct_order_marketing` — revenue, returns, and channel attribution per order item
- `fct_marketing_web_performance` — session-level conversion and engagement metrics
- `dim_user` — user demographics with age segmentation and channel groups
- `dim_products` — product catalog with computed margin metrics

## Key business questions answered

1. Which marketing channels drive the most revenue and conversions?
2. Where do users drop off in the purchase funnel (page_view → cart → purchase)?
3. Which products have the highest return rates and what is their net revenue contribution?

## Interview-ready talking points

1. Built and run in **dbt Cloud** — familiar with the IDE, job scheduling, model lineage graph, and documentation generation.
2. The 3-layer dbt architecture (staging → intermediate → marts) separates source cleaning, business logic, and BI-ready surfaces so each layer is independently testable and replaceable.
3. Traffic attribution in `int_orders_enriched` uses a window function to match the nearest purchase event per order, with fallback to signup source — demonstrates awareness of attribution complexity in e-commerce.
4. The `marketing_channel_group` macro centralizes channel classification so any model can group traffic sources without duplicating CASE logic — same pattern Power BI measures would reference.
5. Cross-adapter Jinja blocks let the project run in CI with DuckDB seeds without BigQuery credentials — demonstrates multi-environment SQL thinking.
6. 73 data quality tests enforce contracts at every layer; source freshness tests were wired up in BigQuery to catch stale data before it reached Power BI.
