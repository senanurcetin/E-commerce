# Unified NEXUS source audit & import

The NEXUS Commerce Intelligence master repository contains **both** E-Commerce
and Greenweez independent dbt projects and the combined Streamlit presentation.
This milestone adds an operational source registry and safer source ingestion.
The following tools use **only local files**: no API calls, credentials or
production data are required to inspect import readiness.

## Source audit (default: no writes or API requests)

Run from the E-Commerce root:

~~~cmd
python -m scripts.nexus_workspace status
~~~

Machine-readable for CI/operator evidence:

~~~cmd
python -m scripts.nexus_workspace status --json
~~~

The output reports eight independent data groups: historical E-Commerce, Greenweez
finance, original Greenweez Google Sheets source observations, consented Commerce Lab GA4 test events, GA4 acquisition, GSC search, PSI
lab runs and local Chrome Lighthouse.

| Status | Meaning |
| --- | --- |
| missing | No local source snapshot. It is NOT measured zero traffic/revenue. |
| invalid | Manifest, schema, input file or a source audit failed. Do not use source numbers. |
| synthetic | Test/seed dataset. Never represent the value as actual business revenue. |
| external_unverified | A source file was imported and schema-valid, but provenance and business totals are not independently certified. |
| api_snapshot | Locally available source-specific API/lab report with supported schema; does not mean live polling, commercial revenue or authoritative business records. |
| api_empty | Valid API source report with zero matching **rows**, or no metrics matching the requested filter. Do not infer zero business activity. |

No report sums revenue, customers, traffic or purchases between business domains.
Even technically valid imported financial snapshots remain
\`real_business_verified=false\` until independently reconciled.

## Safer one-command import of both dbt source domains

The existing adapters remain available for one source at a time. The
unified import CLI reads **existing built DuckDBs read-only**, validates all
requested sources in a temporary staging folder, and only then updates local
gitignored aggregate snapshots. No raw order IDs, users or emails are written.

Example for a **synthetic development-only QA** after building both projects:

~~~cmd
python -m scripts.nexus_workspace import --ecommerce-db target\ci.duckdb --ecommerce-origin synthetic_ci --greenweez-db integrations\greenweez\target\ci.duckdb --greenweez-origin synthetic_demo
~~~

Example for **existing externally supplied DuckDB marts**, still marked
unverified until independent BigQuery/original finance reconciliation:

~~~cmd
python -m scripts.nexus_workspace import --ecommerce-db target\ecommerce_external.duckdb --ecommerce-origin external_unverified --greenweez-db integrations\greenweez\target\gsheet_real.duckdb --greenweez-origin external_unverified
~~~

Neither example builds missing databases, creates GA4 API credentials nor
falsifies any source provenance. Any one of the two sources can be omitted with
its matching \`--*-origin\` argument. An origin is explicitly **mandatory** per
selected file. If any selected source has an invalid model/schema or failed
accounting reconciliations, the workflow fails **before it overwrites either**
previously published snapshot. Staging and output remain gitignored under
\`target/\`.

The source importer checks transaction grain/aggregations, source-specific
marts, reporting dates, distinct order IDs or financial margin equations,
digest and row counts. Greenweez does not inherit any TheLook business IDs.
The \`Commerce Lab\` events are independent **sandbox tests**, not paid checkouts.

## Evidence registry in the UI

The **Overview · Sources** tab now reads the same validated source status
logic and displays the provenance of imported groups, not manufactured
executive numbers. Changing a snapshot path in the sidebar is reflected in
the source registry. The on-demand PageSpeed form starts collapsed, keeping
the business overview visible without scrolling past an onboarding guide.

Existing tabs remain: **E-Commerce · Historical**, **Greenweez · Finance**,
**GA4 Acquisition**, **GSC Organic Search**, **PSI/Lighthouse**,
**Commerce Lab test events** and **Data Contracts**.

## Known real-data gates

- The owned Commerce Lab GA4 web tag is deployed and the owner observed
  legitimate \`lab_*\` Realtime events in Google Analytics. An authorized
  **numeric GA4 Property ID + Data API read role** is still required to export
  those events into the local source registry. Realtime UI observations
  are not automatically a saved API dataset.
- External Greenweez finance requires authorized source read access,
  reconciliation, currency/financial unit validation and correct treatment
  of unresolved refund values. No per-source attributed ROAS is available
  in the upstream financial mart.
- Historical TheLook/E-Commerce model data must be reconciled against the
  actual BigQuery/raw source, not interpreted from CI seeds.
- Google Search Console and PageSpeed have separate source/consent gates.
- Power BI Desktop source files and final visual review remain unverified;
  these Python changes do not edit a PBIX/PBIP on their own.

## CI coverage

\`tests/test_nexus_workspace.py\` checks that an empty workspace reports
seven missing source groups, corrupt/synthetic-Google manifests are rejected,
invalid Lighthouse JSON is not misclassified, all import paths require an
explicit source identity, and failed second-source validation leaves existing
first-source snapshots untouched.

Run:

~~~cmd
python -m unittest discover -s tests -p test_nexus_workspace.py -v
~~~


## Local Greenweez BigQuery import audit visibility

The ninth independent NEXUS source group is `greenweez_import_audit`.
It reads `integrations/greenweez/target/gsheet_real.duckdb` in **read-only**
mode and validates the single `import_audit.source_quality` record. No
order IDs, customer details or monetary totals leave the database.
Missing import → `missing`; invalid/tampered record → `invalid`.
Only a valid, pinned `workintech-working.fvt_gsheet` import audit is reported
as `external_unverified`: four source table row counts and date ranges are
**not** an independent finance audit. The status table in NEXUS and the Power
BI Source Assurance page expose this additional group.


## Reconcile the import audit against actual local source tables

The ninth source is no longer considered `external_unverified` from a
plausible JSON audit alone. NEXUS and the Power BI generator now open
the exact pinned local `gsheet_real.duckdb` read-only and independently
recompute aggregates from the four `analytics.gwz_finance_*` tables.

Required projected columns, row counts, minimum/maximum dates, invalid
dates, per-field zero/negative counts, unique order keys, unique
campaign days and missing shipping/refund links must match the embedded
`import_audit.source_quality` record. Any discrepancy marks the source
`invalid` and prevents publication of that audit's Power BI rows.
Only aggregate numbers are compared; raw IDs and money totals are never
emitted to logs, NEXUS, or Power BI. This is **local structural
consistency**, not independent warehouse provenance or financial
certification. A deliberate edit that preserves all observed aggregates
cannot be ruled out without a trusted cryptographic provenance source.
