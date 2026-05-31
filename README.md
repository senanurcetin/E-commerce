# E-commerce Marketing and Web Performance Analytics

Archive proof for analytics engineering, dbt modeling, and e-commerce reporting design.

## Why this project exists

This repository shows how raw e-commerce events and order data can be translated into reporting models for traffic-source analysis, conversion behavior, and channel performance.

## Portfolio role

`archive proof`

## Business framing

The project is built around two analytics questions:

- Which traffic sources generate the most valuable sessions and orders?
- How should event, order, user, and product data be modeled so BI tools can answer those questions reliably?

## Architecture snapshot

- **Warehouse target:** BigQuery
- **Transformation layer:** dbt
- **Model structure:** staging, intermediate, and marts
- **Consumption layer:** Power BI
- **Project scope:** analytics engineering and reporting design rather than live application delivery

## Key reporting models

- `fct_marketing_web_performance`
- `fct_order_marketing`
- `dim_user`
- `dim_products`

## What this proves

- You can structure analytics projects with layered dbt conventions.
- You can translate marketing and product questions into warehouse-ready fact models.
- You can prepare clean outputs for BI consumption instead of stopping at raw SQL exploration.

## Local setup

```bash
python -m pip install dbt-duckdb
dbt deps
dbt parse --profiles-dir .github/dbt-profiles
```

## Quality checks

The GitHub Actions workflow runs:

```bash
dbt deps
dbt parse --profiles-dir .github/dbt-profiles
```

## Limitations

- This repo focuses on modeling and reporting logic, not dashboard code.
- Cost data is limited, so full ROI and CAC analysis is not the main claim.
- It is kept public as supporting analytics proof, not as a lead portfolio case study.

## License

MIT
