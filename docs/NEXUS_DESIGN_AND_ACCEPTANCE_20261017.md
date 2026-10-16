# NEXUS Commerce Intelligence — Design, source data, GA4 and Power BI acceptance

## 1. NEXUS web dashboard design

The local Streamlit application uses one shared design module
[`dashboard/nexus_theme.py`](../dashboard/nexus_theme.py), applied across
E-Commerce historical marts, Greenweez finance, Greenweez original source
worksheets, GA4, GSC, Commerce Lab test events, and Lighthouse.

Visual hierarchy: editorial NEXUS header; navy gradient canvas; cyan/purple
data accents; readable metrics and legends; pill-style tabs; responsive
spacing and larger hit areas; compact evidence cards and a governance-first
overview. These changes style the **local Streamlit dashboard**, not the
public Vercel storefront and not the user's separate portfolio website.
No metric sources or filters are silently changed by CSS.

## 2. Greenweez source turnover completeness

Audited historical Google Sheets workbook: `Media at Greenweez - orders`,
1–15 August 2021, 12,072 populated source rows.

| Source grouping | Rows | Missing turnover values |
| --- | ---: | ---: |
| is_ga = 1 | 6,758 | 0 |
| is_ga = 0 | 5,314 | 5,314 |
| Total | 12,072 | 5,314 |

- Missingness is precisely conditional on `is_ga=0` in this
  authorized source extract, not random across date/channel.
- Seven source order rows lack `orders_id`; 12,065 known distinct IDs
  were observed, with no duplicate known IDs across the retrieved rows.
- The 5,314 rows without turnover are not assigned zero sales or imputed.
  The known-turnover aggregate is **partial** and cannot be labeled total
  merchant turnover, ROAS, audited revenue, cash settled or margin.
- This pattern establishes a likely structural coverage dependency,
  **not the business cause** of those missing values. The upstream owner
  must confirm the definition of `is_ga`, whether non-GA rows represent
  purchases outside attribution/trackability, and the currency/tax/refund
  basis for `turnover` and `cost`.
- The new validated source contract stores only the integer is_ga coverage
  cross-tab, NOT original order/campaign identifiers.

## 3. Commerce Lab GA4 API data extraction

- Real visitor events are observed in the user's independent Commerce Lab
  Realtime GA4 screen; site `https://nexus-commerce-lab.vercel.app/`.
- Authorized user web stream identifiers are public Measurement ID
  `G-F0B2EQVC8M` and numeric **Stream ID** `16145034201`.
- The **numeric GA4 Property ID** is a separate value and is still
  unknown; neither of the above identifiers can replace it.
- The read-only reporting exporter is implemented in
  [`scripts/lab_ga4_events.py`](../scripts/lab_ga4_events.py), which
  filters exact hostname and allowlisted `lab_*` events.
- [`scripts/ga4_property_preflight.py`](../scripts/ga4_property_preflight.py)
  optionally discovers the right Property ID by matching exact web stream
  name, Measurement ID and public URL against the **authorized**
  Analytics Admin API, rejecting all old ToyStore/portfolio identities.

**API status: BLOCKED on credentials/identity.** The authorized Windows
environment did not have Google Analytics Application Default Credentials or
a `GA4_LAB_PROPERTY_ID` configured. No live Data API totals are claimed.
A Google login in Chrome does NOT automatically authorize Python ADC.

Windows owner action (credentials must stay local):

~~~cmd
cd /d C:\Users\MONSTER\E-commerce
python -m pip install "google-auth[requests]>=2,<3"
python -m scripts.ga4_property_preflight
~~~

To obtain credentials, the owner may use an approved local
`gcloud auth application-default login --scopes=https://www.googleapis.com/auth/analytics.readonly`
flow if the Google Cloud SDK is installed and the Analytics Admin/Data API
permissions allow it. Alternatively, grant an explicitly authorized
read-only service account access in the Analytics UI, then configure
Application Default Credentials securely. Do not commit JSON credentials,
paste bearer tokens into chat, or reuse ToyStore stream details.

Once authorized:

~~~cmd
python -m scripts.ga4_property_preflight --resolve
set GA4_LAB_PROPERTY_ID=<VERIFIED_NUMERIC_PROPERTY_ID>
python -m scripts.lab_ga4_events --start 2026-10-16 --end 2026-10-17
python -m streamlit run dashboard\google_marketing_app.py
~~~

Record extraction date, local timezone, property ID, matched web data
stream and event names. Test checkout is *not* a paid purchase.

## 4. Power BI source and visual acceptance

The NEXUS dark-themed importable Power BI theme in
[`powerbi/themes/nexus-commerce.json`](../powerbi/themes/nexus-commerce.json)
has been aligned with Streamlit tokens. The historical Power BI gallery is not
recaptured by changing JSON.

Source-level QA is automated through
[`scripts/powerbi_acceptance.py`](../scripts/powerbi_acceptance.py)
and CI tests:

- JSON theme structure/design tokens
- DAX KPI names and known attribution semantics
- Whether an editable PBIX/PBIP was actually supplied
- Explicit outstanding gates for real Desktop render, refresh, slicers,
  tooltips, data relationship contexts, mobile layout, and screenshots

**Power BI final Desktop acceptance: HOLD** because an original editable
Power BI source report and authorized model refresh/render evidence are
not available in the E-Commerce repo or identified workstation paths.
Static tests are **not** a substitute for real Desktop screenshot review.

See [`docs/POWER_BI_VISUAL_QA.md`](POWER_BI_VISUAL_QA.md) for the original
three-page checklist, DAX grain caveats and unit corrections.

## 5. Release conditions

- [x] Centralized NEXUS web theme and chart palette
- [x] Source-level is_ga turnover missingness reconciled
- [x] GA4 property identity resolver and Data API exporter source contracts
- [x] Power BI theme and static source acceptance checks
- [ ] Real local GA4 Data API extraction: **requires authorization**
- [ ] Original editable Power BI report and successful actual Desktop refresh
- [ ] Owner/finance confirmation of Greenweez turnover/currency/refunds
- [ ] Screenshots/visual QA of production-specific pages by source identity

Never remove missing-data caveats or synthetic/unverified labels just to
improve public presentation.
