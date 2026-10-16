# E-Commerce integrations / Greenweez

## First-party repo consolidation — isolated dbt subproject

The Greenweez original repository source is incorporated here under
integrations/greenweez/ via a **squashed Git subtree** from:

https://github.com/senanurcetin/greenweez-finance-campaign-analytics

This keeps the Greenweez dbt SQL models, finance and marketing marts, seeds,
unit/data-quality tests, DuckDB profiles and explanatory notes **inside the
E-Commerce GitHub repository**. Its upstream project remains separate and
unmodified for provenance/history. Greenweez's dbt project name
(db t_workintech without the space) and target schema are isolated; it is NOT
merged into the root E-Commerce dbt project.

### Reproduce both projects from the ONE E-Commerce clone

From E-Commerce root:

~~~cmd
python -m pip install -r dashboard\requirements.txt
python -m pip install "dbt-duckdb>=1.10,<2"
cd integrations\greenweez
dbt deps --profiles-dir .github\dbt-profiles
dbt seed --profiles-dir .github\dbt-profiles --target demo
dbt build --profiles-dir .github\dbt-profiles --target demo --exclude resource_type:seed
cd ..\..
python -m scripts.greenweez_bridge --db integrations\greenweez\target\demo.duckdb --provenance synthetic_demo
python -m streamlit run dashboard\google_marketing_app.py
~~~

**These commands build SYNTHETIC sample Greenweez data.** They are for
functional/demonstration tests and should never be shown as real operational
financial performance.

### Actual Greenweez authorized source (future gate)

The nested project includes the upstream fvt_gsheet source strategy and
BigQuery-to-DuckDB read-only loader. Those credentials are not available in
GitHub and are NEVER bundled with this subtree. Only the authorized owner
may use that path and must keep the exported marts gitignored.

When the authorized BigQuery source has been independently extracted, use
the known existing path, e.g.:

~~~cmd
python -m scripts.greenweez_bridge --db integrations\greenweez\target\gsheet_real.duckdb --provenance external_unverified
~~~

The *external_unverified* label remains until real warehouse totals, date
window, refund units, currency and campaign attribution semantics have been
reconciled. No file name or CLI switch certifies real business data.

### CI contract

- Root E-Commerce CI still builds its own original dbt models independently.
- The Greenweez dbt job changes working directory to
  integrations/greenweez, performs dbt deps / seed / build on the nested
  synthetic DuckDB profile, and runs the E-Commerce Greenweez bridge against
  the resulting actual **dbt outputs**.
- The bridge only selects aggregated finance/marketing mart columns; no order,
  customer, email, user ID or campaign identifier is transferred.
- The unified Streamlit app reads only the gitignored validated bridge JSON;
  its visualizations never sum Greenweez revenue with TheLook or Lab events.

For user acceptance and limitations read
docs/NEXUS_UNIFIED_COMMERCE_PLAN.md in the root E-Commerce repository.
