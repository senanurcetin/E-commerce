# NEXUS Commerce Intelligence — Greenweez integration

## One GitHub repository, two isolated dbt projects

The complete Greenweez finance and campaign source was incorporated here under
[integrations/greenweez/](greenweez/README.md) as a squashed Git subtree.
All dbt models, marketing/finance marts, source audits, offline tests and
dashboard code now live in the NEXUS repository. The legacy standalone
Greenweez repository is **not a runtime/CI dependency**. Its administrator
deletion is pending; see the [repository consolidation checklist](../docs/REPOSITORY_CONSOLIDATION.md).

Historical E-Commerce and Greenweez dbt targets and source systems remain
isolated despite sharing one root CI workflow and Streamlit application.
Never add merchant revenues or auto-union their transactions.

### Reproduce both projects from ONE NEXUS clone

From the NEXUS Commerce Intelligence repository root:

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

- Root NEXUS CI still builds its own original dbt models independently.
- The Greenweez dbt job changes working directory to
  integrations/greenweez, performs dbt deps / seed / build on the nested
  synthetic DuckDB profile, and runs the NEXUS Greenweez bridge against
  the resulting actual **dbt outputs**.
- The bridge only selects aggregated finance/marketing mart columns; no order,
  customer, email, user ID or campaign identifier is transferred.
- The unified Streamlit app reads only the gitignored validated bridge JSON;
  its visualizations never sum Greenweez revenue with TheLook or Lab events.

For user acceptance and limitations read
docs/NEXUS_UNIFIED_COMMERCE_PLAN.md in the root NEXUS repository.
