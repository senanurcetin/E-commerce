# NEXUS Google Measurement Dashboard

Status: **implemented as a local web application** with a source-verification gate and an **explicit user-triggered PageSpeed Insights API call**. It is **not deployed** and does not automatically poll Google, and does not represent historical E-Commerce/Olist/Greenweez sales as Google-measured events. No demo or synthetic business metrics are substituted for absent accounts.

## Windows CMD · first real site audit (Python 3.11+)

The old screen's missing-manifest warning means there is no validated Google snapshot yet. It does **not** mean the app or GitHub installation failed. The dashboard now keeps all tabs accessible and includes a one-click **public PageSpeed audit**.

From a local checkout of this repo, update and launch:

~~~cmd
cd /d %USERPROFILE%\E-commerce
git pull origin main
python -m pip install -r dashboard\requirements.txt
python -m streamlit run dashboard\google_marketing_app.py
~~~

Open http://localhost:8501 . In **GET STARTED · Run your first real PageSpeed audit**, enter your own public website, for example the HTTPS URL of your published portfolio (not localhost), choose Mobile or Desktop, and click **Run real PageSpeed audit**. The URL is submitted to Google's PageSpeed Insights service on your explicit request only. The API may apply a quota or require an optional `GOOGLE_PAGESPEED_API_KEY`; no synthetic results are shown if Google denies the request.

The app automatically writes a time-stamped JSON snapshot under gitignored `target/google_measurement/`, then produces a validated `marts/manifest.json` and source-specific CSV files. It refreshes the report. GA4 and GSC remain **Not connected** until their *own* read-only property credentials are configured.

### Manual collector alternative (no GA4/GSC property required)

~~~cmd
python scripts\google_measurement.py pagespeed --url https://YOUR-PUBLIC-SITE --strategy mobile
python scripts\google_measurement.py pagespeed --url https://YOUR-PUBLIC-SITE --strategy desktop
python scripts\google_measurement_marts.py
python -m streamlit run dashboard\google_marketing_app.py
~~~

Do not run the mart builder **before** collecting a real snapshot; it rightly rejects empty inputs.

### GA4 and Search Console later

The GA4 Data API needs a numeric GA4 Property ID and read-only account authorization; GSC needs the exact verified site property and authorized read-only API access. Follow `docs/GOOGLE_MEASUREMENT_INTEGRATION.md`. They are *separate optional connectors*; the PageSpeed workflow works independently.

For shared/public deployment, an authentication and data-exposure review is required before enabling on-demand API use. This is currently a **local-only** personal dashboard, not a hosted public scanning service.

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
- Without a manifest, **onboarding remains accessible** and each source displays Not connected. A validated *single source* is sufficient: the exporter creates header-only CSVs for unconnected sources. Corrupt manifests, unsupported versions, source mismatch, row-count mismatch and partial extractions are rejected before displaying business KPIs.
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
