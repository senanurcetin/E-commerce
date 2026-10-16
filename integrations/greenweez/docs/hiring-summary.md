# Reviewer brief — Finance and Campaign Analytics Engineering

**Role:** Analytics engineering, dbt modeling, SQL quality testing and finance/marketing KPI design. **Demo dataset:** synthetic — not Greenweez's actual financial performance.

## Problem solved

Combine order-level margin, logistics costs and advertising spend in a reporting layer that preserves missing-fulfillment and ad-only days, so business users can inspect profitability and campaign efficiency without misleading denominators.

| What to inspect | Evidence |
|---|---|
| How are operational metrics defined? | [Documented formulas](../README.md#architecture): `operational_margin`, `ads_margin`, `roas`, `margin_roas`, CPC and CTR |
| How are different sources handled? | [Source model documentation](../README.md#source-systems-gwz_raw-default-and-fvt_gsheet) and [dbt models](../models/) |
| Does the model reconcile? | [dbt singular and schema tests](../tests/) and [CI design](../README.md#quality-checks-ci) |
| Can a reviewer run it without a cloud account? | `make demo` against synthetic DuckDB records; [setup and demo](../README.md#quick-start-duckdb-demo-no-cloud-account-needed) |
| What happens in the UI? | [Streamlit source](../demo/app.py) and [architecture diagram](finance-campaign-pipeline.svg) |

## Decisions demonstrated

- Explicit cost and margin formulas with testable data-grain assumptions.
- Correct weighted aggregation across days, including days with advertising spend but no orders.
- Dual warehouse compatibility (BigQuery for actual source systems, DuckDB for portable examples).

## Non-claims

No production attribution or real Greenweez ROI is proven. The local demo uses intentionally small synthetic data; the real source tables are not populated as part of this repository's BigQuery workflow. Business figures should be recalculated on authorized source data before decision-making.

**Full methodology:** [Project README](../README.md).
