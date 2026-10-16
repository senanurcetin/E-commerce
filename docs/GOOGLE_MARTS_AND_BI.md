# Google Measurement → Source-Isolated BI Marts

This is a **local, read-only staging/export workflow** for *actual* GA4 Data API, GSC Search Analytics API and PageSpeed Insights snapshots. It does not connect accounts, schedule API calls, write to BigQuery, or generate example business figures. It deliberately does **not** join the existing historical E-Commerce facts, Olist public data, or Greenweez finance metrics.

## Run

1. Retrieve one or more authorized snapshots with [the Google measurement collector](../scripts/google_measurement.py), after configuring the relevant property's least-privilege read access.
2. Build the source-specific CSV extracts:

~~~bash
python scripts/google_measurement_marts.py --input-dir target/google_measurement --output-dir target/google_measurement/marts
~~~

3. Review `target/google_measurement/marts/manifest.json` and the three CSVs before importing them into Power BI or any warehouse.

The exporter **fails if there are no real snapshots**. It rejects incomplete/partial API results unless the operator explicitly runs with `--allow-partial`, in which case the manifest records the number of incomplete snapshots. A partial extract is not suitable for a production KPI without an explicit coverage label.

Generated files remain under the existing gitignored `target/` directory. Never commit them if they contain private account or property identifiers.

## Export contracts

| File | Source | Unique grain | Important constraints |
|---|---|---|---|
| `ga4_channel_daily.csv` | GA4 Data API | property ID + date + session-default-channel | Count metrics nonnegative; engaged sessions ≤ sessions; active users **not additive** across rows |
| `gsc_device_daily.csv` | GSC Search Analytics API | site property + date + device | CTR is a ratio in [0,1], average position not directly additive, clicks ≤ impressions |
| `pagespeed_lab_audits.csv` | PageSpeed Insights | URL + strategy + extraction timestamp | Scores 0–100, Lighthouse **lab** metrics, not real-user CrUX |

All rows are explicitly labeled by their source. Duplicate rows *within one snapshot* are rejected. When multiple snapshots cover the same source/property/day/grain, the **latest extracted** row is retained—not summed. Conflicting values recorded with an identical extraction time are rejected. Exports with more than one property remain separate; no cross-property revenue sum is authorized.

### Correct BI semantics

- **GA4 purchases / sessions:** use the property and report period from the source. Sum session-channel rows only at validated grains; GA4 `active_users` is an estimated distinct metric, so simply summing daily/channel active users can double-count people. For cross-day distinct users, request the suitable GA4 reporting aggregation directly.
- **GSC impressions, clicks:** additive across *mutually exclusive* device/day rows within the same site property and search reporting mode. For a grouped CTR, calculate `SUM(clicks) / NULLIF(SUM(impressions), 0)`. Grouped average position should use an impressions-weighted mean, not `AVG(average_position)`.
- **PageSpeed:** each audit is a point-in-time Lighthouse run. Preserve each URL/device/time combination. Do not average lab scores into a "real-user" Core Web Vitals metric. Add CrUX history before presenting field LCP/INP/CLS.
- **Advertising CAC/ROAS:** requires source-verified Google Ads cost and a documented conversion/value attribution model. No such join is created in this PR.
- **E-Commerce and Greenweez:** time series and attribution identifiers are not known to match new Google properties. BI should present these as **different datasets**, not as one reconciled business ledger.

### Power BI approach (no paid license required)

Load the three CSVs as **separate source tables**, each with an independent date dimension where appropriate. Build these report pages:

1. **Web Acquisition (GA4):** session trends, engaged-session rate, purchases (source-qualified), GA4 channel mix and unavailable-state notices.
2. **Organic Search (GSC):** clicks, impressions, impression-weighted CTR and average position, with device filters. Do not interpret GSC clicks as GA4 sessions.
3. **Site Experience (PSI):** latest Lighthouse score by URL/mobile/desktop and time-stamped lab diagnostics; label CrUX as unavailable until authorized field data exists.
4. **Commerce / Greenweez:** remain on their existing data models and display an explicit source switcher and data provenance. Do not cross-filter unrelated properties as if they shared customer/order IDs.

The NEXUS theme already stored at `powerbi/themes/nexus-commerce.json` can be applied to the actual desktop report once the editable `.pbix` or `.pbip` is available.

### BigQuery integration gate

The CSVs are staging extracts, **not production BigQuery tables**. Before loading: select the authorized project and dataset; confirm API property ownership, timezone, currency, security, budget and desired retention; create isolated source-specific datasets; load with a fixed schema; run row-grain and freshness dbt tests; then reconcile to the appropriate Google reporting UI. Use scheduled extraction only when these checks pass.

## Reproducibility

CI executes offline tests for malformed metric values, mismatched grains, partial extracts, overlapping exports, separate account scopes, and report file generation. CI makes no authenticated Google requests and incurs no BigQuery charges.

Related docs: [Google APIs and access requirements](GOOGLE_MEASUREMENT_INTEGRATION.md), [Power BI visual acceptance](POWER_BI_VISUAL_QA.md).
