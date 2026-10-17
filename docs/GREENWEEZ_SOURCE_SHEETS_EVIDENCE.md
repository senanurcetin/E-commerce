# Original Greenweez Google Sheets — source observations, not certified finance

This is a **separate authenticated source-observation product** inside the
NEXUS Commerce Intelligence product repository. It does NOT alter the original Greenweez dbt models
or certify their finances.

The authorized owner account exposes two Google Sheets workbooks:

- Media at Greenweez - orders: tab orders, columns
  date_date, orders_id, new, turnover, is_ga, channel_grouping, channel,
  campaign_key and campaign.
- Media at Greenweez - campaigns: tabs adwords, bing, facebook, criteo,
  columns date_date, campaign_key, paid_source, campaign_name, cost,
  impression and click.

**Historic scope:** These are 2021 historical workbook observations, not
2026 live e-commerce traffic or a current payment provider. The previous
Greenweez finance dbt / BigQuery example covers a potentially different
2021 time interval. The two are deliberately NOT joined on date or campaign.

## Snapshot contract

A read-only query of the authorized workbooks aggregates in memory and
writes **only** date-level totals into a **gitignored local file**:

target/greenweez_bridge/google_sheets_observed.json

Required snapshot source fields:

- schema_version = 1
- source_system = greenweez_google_sheets_aggregate_observed
- data_status = source_observed_financial_semantics_unverified
- observed_at_utc = extraction time
- source_sheets = the two named workbooks
- row_counts = source order worksheet and campaign worksheet row counts
- daily_orders = ISO date, order_rows, distinct_order_ids (KNOWN IDs only), missing_order_ids, missing_turnover_rows, turnover_as_stored (sum of NONBLANK values)
- daily_campaigns = ISO date, paid_source, campaign_rows, cost_as_stored,
  impressions, clicks and missing_cost_rows / missing_impressions_rows / missing_clicks_rows

**Source privacy:** Order IDs and campaign IDs/names are used only in
memory, to count unique orders and validate source rows; none is exported.
Customer personal data are not requested at all. The E-Commerce repository
contains only code, a schema validator, UI and TEST-ONLY fixtures. The source
snapshot remains on the authorized machine under ignored target/.

**Completeness warning:** If any order rows have missing order IDs, those rows remain in worksheet row/turnover totals, but cannot contribute to distinct IDs. The unique-ID figure is therefore a lower bound, never a certified paid-order count.

**Completeness:** Any row with blank turnover remains in worksheet row totals and contributes to missing_turnover_rows; no missing monetary value is silently interpreted as zero. Likewise blank campaign numeric cells are counted separately. Charts display only sums of observed numeric values.

**Financial semantics are not certified:** The turnover and cost columns are
shown as stored, without an asserted currency or FX conversion, and the
order row count is not certified net paid/fulfilled orders. This module
never computes campaign-attributed revenue, ROAS, profitability or official
net sales. Clicks and impressions are ad-platform source observations,
not GA4 sessions or conversions.

## Dashboard

The existing local NEXUS Streamlit dashboard gains a separate
**Greenweez · Source Sheets** tab, next to Greenweez · Finance.

- The original dbt Greenweez finance module remains isolated.
- The source-sheet observations have their own separate daily turnover and
  ad-cost plots, explicit UNVERIFIED financial semantics banner and no
  per-order/customer identifiers.
- If no authenticated source snapshot exists, the tab states "not imported"
  without inventing financial KPI values.
- The Overview · Sources page shows this as an eighth distinct source, and
  the CLI reports it as external_unverified, never as verified finance.

Run a local source audit after the authorized owner import:

~~~cmd
cd /d C:\Users\MONSTER\E-commerce
python -m scripts.nexus_workspace status
python -m streamlit run dashboard\google_marketing_app.py
~~~

## Acceptance gates

- [x] Two source workbooks verified accessible via the owner's authorized account
- [x] Aggregate-only schema and source-grain / count validation implemented
- [x] Separate NEXUS UI and source audit entry (no financial cross-joins)
- [ ] Full authorized spreadsheet aggregation imported on owner's machine
- [ ] Source worksheet row coverage, duplicate IDs and empty values reviewed
- [ ] Independent reconciliation of turnover, cost, refunds, currency and
      vendor definitions performed before any actual-finance KPI claim
- [ ] Date window / campaign linkage reconciled separately with Greenweez dbt
- [ ] Streamlit live screenshot visually reviewed after valid local import

Do not commit local source snapshot, customer IDs or paid campaign names.
