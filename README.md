# E-commerce Marketing and Web Performance Analytics

This project models e-commerce behavioral and transactional data using **dbt + BigQuery** to support downstream reporting in **Power BI**.

## Business Questions

This analytics project focuses on two domains:

1. **Website Performance**
   - What are the main website traffic sources?
   - How do traffic sources affect conversion behavior?
   - Are there usability or funnel bottlenecks visible in website interaction data?

2. **Marketing Effectiveness**
   - Which marketing channels generate the most valuable traffic?
   - How do different channels compare in terms of completed orders and revenue?
   - Which customer segments respond better to different acquisition sources?

## Tech Stack

- **BigQuery** for raw and transformed storage
- **dbt** for data modeling and testing
- **Power BI** for dashboarding and reporting

## dbt Modeling Layers

### Staging
Raw source cleanup and standardization:
- `stg_events`
- `stg_order_items`
- `stg_users`
- `stg_products`

### Intermediate
Enriched business-ready transformation layer:
- `int_events_enriched`
- `int_orders_enriched`

### Marts
Final reporting models:
- `dim_user`
- `dim_products`
- `fct_marketing_web_performance`
- `fct_order_marketing`

## Final Fact Tables

### `fct_marketing_web_performance`
Session-level fact table used for:
- sessions
- conversion flags
- session duration
- traffic source analysis
- browser analysis
- time-of-day analysis

### `fct_order_marketing`
Order-item-level fact table used for:
- revenue
- returned revenue
- completed order counts
- category / brand analysis
- traffic source performance

## Data Quality

dbt tests are used for:
- `not_null`
- `unique`
- `relationships`
- `accepted_values`

## Notes and Limitations

This dataset does not include direct campaign cost fields, so:
- **ROI cannot be calculated directly**
- **CAC cannot be calculated directly**

Instead, the project focuses on proxy metrics such as:
- revenue by traffic source
- session conversion signals
- completed orders by channel
- user segment performance

## Next Step

The marts are designed to be consumed directly in Power BI for dashboarding.