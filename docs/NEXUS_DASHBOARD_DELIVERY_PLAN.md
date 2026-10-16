# NEXUS Commerce Intelligence — Dashboard Delivery Plan

Date: 2026-10-16. This roadmap is tied to actual user acceptance screenshots and separates implementation from access gates.

## Evidence from Windows desktop run

The NEXUS Streamlit app launches successfully but initially displays **Validated snapshot manifest not found**. This is a legitimate empty-data state: the CSV exporter had not received an API snapshot. It must be a self-service onboarding flow, not a blank, blocking warning panel.

## Iterative release gates

| Phase | Work | Done when | Current state |
|---|---|---|---|
| 1 — Entry & usability | Replace blocking empty-manifest screen with source tiles, available tabs and first-run guidance | Clean install stays navigable with no fake KPIs | Implemented in this PR; CI acceptance pending |
| 2 — Public web diagnostics | Run real PageSpeed Insights scans on demand, store snapshots and refresh validated CSVs | A public HTTPS URL produces mobile or desktop Lighthouse results without GA4 credentials | Implemented in this PR; real API smoke pending local operator |
| 3 — Observability UX | Display NEXUS source states, Lighthouse score/device comparison, lab LCP history and provenance | The visible report distinguishes measured/missing sources and lab/field metrics | Implemented in this PR; desktop design review pending |
| 4 — Automated regression | Pure Python unit tests, Streamlit AppTest empty/PageSpeed-only/full-data states, existing dbt CI | CI jobs green; no network/credentials/test figures leave fixtures | Tests added; CI acceptance pending |
| 5 — Authenticated acquisition | GA4 and GSC property IDs, read-only credentials, timezone/currency reconciliation | Source totals independently match real Google UIs | Blocked on actual property authorization |
| 6 — Warehouse & ads | Source-specific BigQuery tables, freshness contracts, verified Ads spend and CrUX field metrics | Access approved, warehouse counts/finance semantics reconciled | Planned, not yet connected |
| 7 — Portfolio/publishing | Validate PBIX/PBIP locally, capture professional dark NEXUS visuals, deploy private/public web app with access controls | Screenshots reflect real validated datasets, hosted access/security reviewed | Planned, no public deployment |

## Nonnegotiable measurement boundaries

- No fabricated production traffic, revenue or paid-channel ROAS.
- PageSpeed Lighthouse scores are **laboratory** benchmarks, not real-user Core Web Vitals.
- GA4 and Search Console must each be linked to their own verified properties.
- Olist and Greenweez are separate business datasets; no implicit date/channel joins.
- The new PageSpeed form is a **user-triggered** local action, not a background task, and sending a URL to Google requires an explicit click.
- Source exports remain gitignored under target/.
- This PR is not proof of a successful live Google API run: unit tests use mocked API results and Streamlit smoke tests use local CI-only fixtures.

## Windows acceptance check

1. Run `git pull origin main` from `%USERPROFILE%\E-commerce` after CI merge.
2. Run `python -m pip install -r dashboard\requirements.txt`.
3. Run `python -m streamlit run dashboard\google_marketing_app.py`.
4. With no manifest, verify the three source tiles show Not connected, all tabs remain visible, and the PageSpeed form is usable.
5. Provide a public HTTPS portfolio URL; execute a real Mobile PageSpeed scan and verify its reported value and Google source timestamp. Repeat for Desktop when desired.
6. Check that GA4 and GSC remain Not connected and PageSpeed has at least one validated row.
7. Check portal usability on Windows at laptop resolution; preserve evidence screenshots only after source reconciliation.

The original interactive Power BI report is not in this repository; unchanged legacy screenshots must not be claimed as refreshed.
