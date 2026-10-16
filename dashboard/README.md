# NEXUS Google Measurement Dashboard

Status: **implemented as a local, read-only web application** with a source-verification gate. It is **not deployed**, does not query Google in real time, and does not represent historical E-Commerce/Olist/Greenweez sales as Google-measured events. No demo or synthetic business metrics are substituted for absent accounts.

## Quick start (Python 3.11+)

~~~bash
python -m pip install -r dashboard/requirements.txt
# Configure access and collect REAL aggregate Google measurements using:
# docs/GOOGLE_MEASUREMENT_INTEGRATION.md
python scripts/google_measurement_marts.py --input-dir target/google_measurement --output-dir target/google_measurement/marts
streamlit run dashboard/google_marketing_app.py
~~~

Without authenticated GA4/GSC/property reports or PageSpeed API results, the dashboard displays **unavailable-state guidance**, not fake KPIs. Collector snapshots are saved under gitignored target/google_measurement. The separate CSV mart exporter checks source, date, grain, duplicates, partial extraction and schema before generating the manifest.

### Pages

| Dashboard view | Real source | Supported metrics | Explicit non-features |
| --- | --- | --- | --- |
| GA4 · Acquisition | GA4 Data API | sessions, engaged sessions, engagement ratio, e-commerce purchases, purchase revenue (GA4 property currency), daily source trends | Active users are not summed across dates/channels; neither validated orders nor Ads spend is inferred |
| GSC · Search | GSC Search Analytics API | search clicks, impressions, clicks/impressions CTR, impression-weighted search position, device/time filters | GSC clicks are not GA4 sessions |
| PSI · Lighthouse | PageSpeed Insights API | URL/device latest lab scores (performance, accessibility, best practices, SEO), LCP/CLS/TBT lab diagnostics | No field CrUX/INP claim |
| Measurement Contracts | Source manifest, safeguards | source isolation, privacy, limitations | No partial or simulated source figures |

Palette: **NEXUS navy/cyan/purple**, responsive Streamlit Plotly figures, time filters, property selectors and download buttons for the already verified aggregate rows. Everything works with open-source tools and does not require a Power BI Pro license. The original Desktop PBIX/PBIP is not present in the repository, so this viewer is not a surrogate validation of existing Power BI screenshots.

### Metric correctness

- The dashboard selects **one GA4 property at a time**. Active users is a distinct metric and is deliberately not summed; real user counts over arbitrary windows must be queried at the desired aggregation grain from GA4 directly.
- Search Console selects **one verified site property at a time**. CTR is total clicks / total impressions. Average position is impressions-weighted. Device filters apply before summing metrics.
- PageSpeed selects the **latest audit per page URL and device strategy**; a score of 0 is valid, not missing. Lighthouse lab diagnostics are separate from real-user CrUX field Core Web Vitals.
- Missing or incomplete API export files fail closed; the dashboard will not fabricate numbers. Corrupt manifest, unsupported schema versions, source mismatch, row-count mismatches and partial sources are rejected.
- Ads spend and conversion attribution are not available; true Google Ads CAC and ROAS **cannot** be calculated. Neither Google report is ever joined to legacy E-Commerce orders or Greenweez finance records.
- Dates, names and reported values in any user export remain tied to the actual source property and its business time zone; the app does not imply a unified global time zone.

### Review & QA

- Offline contract tests: python -m unittest discover -s tests -p 'test_google_measurement*.py' -v
- Dashboard CLI: streamlit run dashboard/google_marketing_app.py
- CI smoke test: tests/smoke_google_marketing_app.py using Streamlit AppTest on empty and synthetic isolated **test-only** export fixtures, plus dbt CI run.
- Source authorization and a fresh live account reconciliation are **outside CI**; publishing a public dashboard requires an access policy and appropriate masking of account/property IDs.
- Google Sheets Greenweez campaign linkage is developed in its separate repository: https://github.com/senanurcetin/greenweez-finance-campaign-analytics/blob/main/docs/GOOGLE_SHEETS_CAMPAIGN_LINKAGE.md .

## Further product gates

1. Configure GA4 and GSC read-only property access and compare totals with their UIs.
2. Load externally measured data to source-qualified BigQuery tables using reviewed service identity and cost controls (the chat connection to BigQuery is not available at present).
3. Implement CrUX API field metrics and Google Ads account cost after authorizing and validating sources.
4. Apply NEXUS measures within actual Power BI Desktop and re-capture screenshot evidence after reconciliation.
5. Deploy an authenticated/appropriate-access dashboard; this PR does not publish a public live app.
