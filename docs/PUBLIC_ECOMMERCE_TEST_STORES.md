# Public Storefronts versus Warehouse Datasets

## What the earlier project actually contains

The E-Commerce dbt pipeline models the historical tables **events, order_items, products, users** from a BigQuery raw staging dataset. Those fields and their product/session/order behavior match the structure of Google's public **TheLook eCommerce** learning dataset, which describes a **fictional online clothing shop with synthetic records**. No controlled TheLook public storefront URL, owned GA4 property, or GSC ownership proof is included in the repository. The historic BigQuery import may use tables copied from TheLook, but we must not assert a verified same-site live feed without stronger warehouse lineage.

**Do not infer a website URL from the public dataset.** The local DuckDB seeds are generated test fixtures, not a replacement for actual browser-side analytics events.

## Verified public shops for on-demand Lighthouse testing

| External test site | Public HTTPS URL | Purpose | Source relationship |
| --- | --- | --- | --- |
| Tricentis Demo Web Shop | https://demowebshop.tricentis.com/ | Product catalog, cart, website responsiveness and mobile/desktop Lighthouse diagnostics | Unrelated independent test website |
| nopCommerce Demo Store | https://demo.nopcommerce.com/ | Second storefront benchmark and visual comparison | Unrelated independent test website; demo may reset hourly |

Both are optional presets in the NEXUS Streamlit PageSpeed form. The selector only **prefills** a URL. Network requests occur only after the user explicitly clicks **Run real PageSpeed audit**. Scores, if returned by Google, are genuine **Lighthouse laboratory audits of the third-party site's public pages**, not our own site's Core Web Vitals or sales funnel. An API quota/permission failure must be shown, not filled with synthetic values.

### Google option for real-world analytics learning

Google maintains a [GA4 demo account](https://support.google.com/analytics/answer/6367342?hl=en) featuring the Google Merchandise Store's aggregate acquisition, engagement and ecommerce reports. Account access is viewer-level and is a legitimate way to study ecommerce reporting.

**Important API restriction:** Google's documentation explicitly states that the demo properties cannot be used with the **Google Analytics Data API**. The existing Python GA4 collector **cannot** authenticate to Google's demo property, even after the user gains viewing access. Do not suggest setting its public demo property ID as a workaround.

For programmatic SQL experiments, Google instead provides a separate [public obfuscated GA4 BigQuery dataset](https://developers.google.com/analytics/bigquery/web-ecommerce-demo-dataset):
`bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`. The historic window is **2020-11-01 to 2021-01-31**. It intentionally contains masked/placeholder values, so it must not be reconciled as a one-to-one extract of Google's live demo account or joined to TheLook's orders by date/user ID.

BigQuery pricing/permissions are separate. BigQuery Sandbox or free-tier allowances may suffice, but direct access still requires a Google Cloud project and enabled BigQuery API.

### Correct project architecture

1. **TheLook-style dbt commerce analysis** — existing synthetic public warehouse dataset, meaningful for SQL/dbt/Power BI KPIs. Do not call its row-level transactions real customer behavior.
2. **Independent test-storefront UX / PageSpeed** — collect Lighthouse lab audits on Tricentis/nopCommerce manually; no sales transactions or GA4 permissions come with these public domains.
3. **Official Google GA4 demo learning** — inspect GA4 reports in Google's UI, not its API; optional public obfuscated BigQuery sample could power **another named dataset** only if formally integrated.
4. **Owned store instrumentation (future)** — if we require our own conversion events, build or deploy a storefront we control, instrument GA4/GTM with privacy/consent controls, and collect genuine traffic separately. Never imply it produced the legacy TheLook orders.

The user's personal portfolio domain is a separate website and should not be used as an ecommerce storefront or presumed to have produced the historical order data.

## Windows first-run

After updating the repository, start the app at `http://localhost:8501` and expand **GET STARTED · Run your first real PageSpeed audit**. Under **E-commerce demo site** select **Tricentis Demo Web Shop**. The Website URL field will fill in automatically. Choose Mobile, then explicitly run the audit. If Google's API succeeds, a timestamped snapshot appears in the gitignored `target/google_measurement/` directory and new Lighthouse data is displayed. Repeat on Desktop or select nopCommerce for a second comparison.

Selecting any preset does not trigger a real API call, alter third-party state, or authorize transactions.
