# NEXUS Historical E-Commerce Marts — Source Isolation

E-Commerce is the unified product repository. In addition to in-repo Greenweez
finance and the new owned Commerce Lab GA4 instrumentation, the same Streamlit
entrypoint includes an E-Commerce historical analytics tab.

## Data and semantics

This source reads **only aggregate columns**, independently from two existing
E-Commerce dbt marts:

| dbt source | Grain and output | What it does not assert |
| --- | --- | --- |
| analytics.fct_order_marketing | Daily completed **distinct order IDs**, returned distinct order IDs, sum of completed line revenue and returned line revenue | This is NOT Commerce Lab checkout activity |
| analytics.fct_marketing_web_performance | Daily session count, sessions with purchase event, page_view event count | Session purchase indicator is not a verified order item or marketing attribution |

Both marts come from historical E-Commerce/TheLook-style data, not from
Greenweez, personal portfolio visits, or the owned NEXUS test website.
No user IDs, raw emails, addresses or raw order IDs leave DuckDB.

## Build & run from ONE repository

Requires root E-Commerce dbt project seed/model run on a local DuckDB profile:

~~~cmd
cd /d C:\Users\MONSTER\E-commerce
python -m pip install -r dashboard\requirements.txt
python -m pip install dbt-duckdb
dbt deps --profiles-dir .github\dbt-profiles
dbt seed --profiles-dir .github\dbt-profiles
dbt run --profiles-dir .github\dbt-profiles
python -m scripts.ecommerce_marts_bridge --db target\ci.duckdb --provenance synthetic_ci
python -m streamlit run dashboard\google_marketing_app.py
~~~

**This command loads root CI seed data, which is SYNTHETIC.** Its values are
strictly for demonstrating/validating model semantics and the reporting flow.
The dashboard visibly labels its source provenance; it must never be
presented as real TheLook sales performance.

For an independently provisioned warehouse-exported DuckDB built from
authorized historical data, use the explicit **external_unverified** source
flag. The bridge will not grant a self-verified source status merely on a flag.
Actual BigQuery totals, date/currency units, return semantics and Power BI
source measures require independent reconciliation first.

The adapter writes a gitignored E-Commerce
target/ecommerce_bridge/snapshot.json with SHA256 of the source DuckDB,
aggregation date, row counts and strict fields. The same NEXUS dashboard
reads this file via **E-Commerce · Historical**.

## Presentation and modeling boundaries

- Completed order count is distinct order IDs **per order date**, avoiding
  the order-item overcount in prior dashboard screenshots.
- Completed revenue is sum of revenue on completed lines, not all statuses.
  Returned amount is maintained separately.
- The session event model is never joined to historical order lines in this
  source adapter. Session converted events are event indicators, not a
  directly validated count of checkout transactions.
- No Greenweez revenue or Lab test checkout event is included in historical
  E-Commerce totals.
- No synthetic fixture is published as an actual financial result.
- No cross-domain ROAS, CAC, LTV, funnel attribution or consolidated turnover
  is inferred from incompatible source systems.

## Test acceptance

- Root dbt CI builds synthetic seed tables and all E-Commerce marts.
- New source adapter runs against the **actual root CI-built DuckDB** marts,
  not merely mocks, and validates the export.
- Offline unit tests exercise distinct order counts, missing/fake sources,
  nonfinite amounts, unexpected raw identifier fields, and source isolation.
- Streamlit AppTest loads a CI-only source fixture and checks historical
  metrics remain separate from Greenweez and Lab data.
- Actual BigQuery/Power BI source and business KPI acceptance remain future
  manual release gates.
