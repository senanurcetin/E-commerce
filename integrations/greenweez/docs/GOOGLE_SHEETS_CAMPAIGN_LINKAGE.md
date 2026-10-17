# Google Sheets Campaign-Key / Orders Coverage Audit

**Status:** Source workbook schemas inspected, without storing credentials or raw data. The reporter identifies conservative campaign-key linkage coverage. It is NOT a causal attribution or ROAS model.

## Discovered, authorized source structure (16 October 2026)

| Workbook | Tab | Fields | Sample period |
| --- | --- | --- | --- |
| Media at Greenweez - orders | orders | date_date, orders_id, new, turnover, is_ga, channel_grouping, channel, campaign_key, campaign | August 2021 |
| Media at Greenweez - campaigns | adwords | date_date, campaign_key, paid_source, campaign_name, cost, impression, click | August 2021 |
| Media at Greenweez - campaigns | bing | same seven fields | August 2021 |
| Media at Greenweez - campaigns | facebook | same seven fields | August 2021 |
| Media at Greenweez - campaigns | criteo | same seven fields | August 2021 |

**Critical normalization issue:** the orders spreadsheet returns Google Sheets date serials for dates when using unformatted values, but the campaigns tabs return ISO date strings. Direct comparisons of those raw values produce false zero matches. The implementation normalizes both to ISO dates.

### Bounded read-only sample

Among the first **1,199 source order rows retrieved**, **1,198 were usable order rows**; **124 had a campaign key**, while **73** found an exact normalized day + campaign key in the read campaign source rows. This is **6.1% of inspected orders** and **58.9% of keyed orders**. Four campaign tabs supplied **673 campaign rows**. None of the 73 sample matches had multiple platform assignments.

This is an initial limited sample and must **not** be extrapolated to a complete order population. Neither the complete order count nor full-period match rate has been established by the sample. No private order/campaign IDs were committed.

## Read-only full workbook audit

The script uses Google Sheets Values API over Application Default Credentials; it has a single read-only scope and never writes to Google or BigQuery. Configure access to both workbooks for the executing principal; keep all credential files outside Git. With Python 3.11+:

~~~bash
python -m pip install "google-auth[requests]>=2,<3"
export GWZ_ORDERS_SHEET_ID="YOUR_ORDER_WORKBOOK_ID"
export GWZ_CAMPAIGNS_SHEET_ID="YOUR_CAMPAIGNS_WORKBOOK_ID"
python scripts/audit_sheet_campaign_links.py --output-dir target/gsheet_audit
~~~

On Windows PowerShell use the $env:GWZ_ORDERS_SHEET_ID and $env:GWZ_CAMPAIGNS_SHEET_ID variables.

The gitignored output directory contains a coverage manifest and a source-level CSV summary with spend, clicks, impressions, matched-order count and matched turnover. No raw order IDs, campaign IDs, campaign names or customer data are exported. Synthetic fixture tests require no Google account.

The audit rejects schema drift, duplicate order IDs, duplicate platform/day/key rows, invalid amounts/counts, missing campaign sources or empty data. An order with a campaign key matching multiple ad platforms on the same day is **ambiguous**, and is not credited to any single platform. Unmatched and blank-key orders are counted explicitly.

## Analytical boundaries

1. A shared campaign_key and day are a possible linkage, not proof of campaign causality, accurate credit allocation, unique visitor identity or return on ad spend. The meaning of is_ga must be verified; it is not automatically a GA4 flag.
2. Missing keys are extensive in the bounded sample. **Never** divide matched subset turnover by all spend and present it as true campaign ROAS. Matched revenue can be biased.
3. The campaign-key source observed here covers **August 2021**. The repo's separate Fivetran/BigQuery Greenweez finance export is **October 1–15, 2021**. E-Commerce historical data and present-day GA4/GSC are other domains. Do not conflate those sources or join by calendar date alone.
4. The original finance refund unit is unresolved; this audit does not change financial margins or refund handling.
5. Platform-level expense, time zone, currency, attribution window and conversion attribution semantics must be verified against original systems before promising per-campaign financial performance.

## Acceptance gates

- Read the *entire* authorized orders and campaign tabs and compare row counts, dates and totals against source Sheets.
- Verify campaign key namespace uniqueness and semantics on all four platforms; reconcile ambiguous keys.
- Confirm the relevant campaign period, EUR monetary formats, timestamps and completed/refunded order lifecycle.
- Reconcile source costs to authoritative ad invoices or spend exports and data-quality anomalies.
- Only after these gates, consider a separate clearly labeled provisional source linkage view in Greenweez's Streamlit app. Keep existing blended ROAS metrics independent.

The script is at scripts/audit_sheet_campaign_links.py. The offline tests run from tests/test_audit_sheet_campaign_links.py. The separate NEXUS Google measurement integration is documented in this repository at [Google measurement integration](../../../docs/GOOGLE_MEASUREMENT_INTEGRATION.md).
