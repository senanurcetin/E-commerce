# Google Measurement Integration: GA4, GSC, GTM, Ads and Web Vitals

**Status: read-only connector foundation.** No actual Google property was connected or verified by this PR. The existing historical E-Commerce marts, Olist Kaggle notebooks and Greenweez finance data remain independent evidence domains. Do not blend their customers, orders, timestamps, or marketing spend without a trustworthy shared key and reconciliation.

## Source contracts

| Product | Granularity | Metrics | Status |
|---|---|---|---|
| Google Analytics 4 (GA4) Data API | Verified GA4 property × day × session default channel | sessions, engaged sessions, active users, e-commerce purchases, property-currency purchase revenue | Read-only connector |
| Google Search Console (GSC) API | Verified GSC property × day × device | organic Search clicks, impressions, CTR, average position | Read-only connector |
| PageSpeed Insights | Public HTTPS URL × mobile/desktop × audit timestamp | Lighthouse performance, accessibility, SEO and lab diagnostics | Read-only connector |
| Google Tag Manager (GTM) | Instrumented storefront events | recommended e-commerce event schema | Future owned-storefront instrumentation |
| Google Ads API | Ads account × campaign × day | spend, impressions, clicks and attributed value | Future authorized integration |
| CrUX API | Origin or page × form factor × observation window | field p75 LCP, INP, CLS | Future integration |
| Looker Studio | BI presentation | cross-source visualization with verified provenance | Optional |

**GA4 sessions are not GSC clicks.** GA4 channels are not identical to the existing historical traffic-source taxonomy. Real ad spend is needed for actual CAC and marketing ROAS; sessions/customer is not a cost. GTM is a deployment/tagging system, not a historical data source.

No Google API events can retroactively measure the repo's legacy E-Commerce, public Olist or Greenweez data. The same calendar date or similar channel labels do not justify joining transactions. The portfolio site is not a storefront and must not emit fictitious purchase events.

## Local read-only snapshots

Prerequisites: Python 3.11+, access to the actual Google property, application default credentials with read-only scopes. The following GA4 and GSC commands require installing the optional google-auth[requests] Python dependency. Credentials must be kept outside the Git repository.

~~~bash
python -m pip install "google-auth[requests]>=2,<3"
export GA4_PROPERTY_ID="NUMERIC_PROPERTY_ID"
export GSC_SITE_URL="sc-domain:example.com"
python scripts/google_measurement.py ga4 --start 2026-10-01 --end 2026-10-14
python scripts/google_measurement.py gsc --start 2026-10-01 --end 2026-10-14
python scripts/google_measurement.py pagespeed --url https://example.com/ --strategy mobile
python scripts/google_measurement.py pagespeed --url https://example.com/ --strategy desktop
~~~

On Windows PowerShell set environment variables with $env:GA4_PROPERTY_ID="..." and $env:GSC_SITE_URL="..." instead. Set GOOGLE_APPLICATION_CREDENTIALS to an authorized credential file stored outside the repository, or configure an appropriate ADC login.

Outputs are under gitignored target/google_measurement/. Snapshots include provenance and extraction time. Google-auth import happens only for GA4/GSC calls; unit tests run offline without any credentials. The collector does **not** silently substitute seeded or synthetic records if authentication or an API fails.

For GA4 BigQuery export, the normal dataset is analytics_<property_id> with events_YYYYMMDD tables. Daily tables may receive late events for three days. The Data API follows reporting identity and can disagree with raw BigQuery event sums; reconcile rather than assert equality. Preserve GA4 property's timezone and revenue currency.

For GSC, the property identifier must exactly match the authorized Search Console property; URL-prefix and domain-scoped properties differ. The Search Analytics API returns prioritized, possibly truncated rows, not necessarily a complete clickstream. For volume, use Search Console BigQuery bulk export and distinguish site vs URL impression grains.

PageSpeed Insights reports Lighthouse **lab** measurements; use the CrUX API/History API for real-user Core Web Vitals, especially LCP, INP and CLS. Do not substitute Total Blocking Time for field INP.

## Proposed mart design (do not join to legacy facts yet)

- ext_ga4_channel_day: GA4 property × date × GA4 session default channel. Metrics are UI-aligned GA4 aggregates.
- ext_gsc_device_day: GSC property × date × device. CTR/average position must be aggregated with appropriate impression weighting.
- ext_pagespeed_audit: exact URL × strategy × collected_at, containing Lighthouse lab scores.
- ext_crux_origin_period: origin × form factor × observation window with field p75 LCP, INP, CLS, only where sample coverage exists.
- ext_ads_campaign_day: ads customer × campaign × date, with account currency and explicit attribution settings.

Every external view must contain source_system, property/site ID, measurement interval, data status and extraction time. Missing live accounts should display "not connected" instead of plausible-looking numbers.

## GTM and instrumentation rollout gate

GTM must be installed only in source code of an authorized e-commerce storefront after consent/measurement review. Implement and QA recommended GA4 e-commerce events: view_item_list, select_item, view_item, add_to_cart, remove_from_cart, begin_checkout, add_shipping_info, add_payment_info, purchase, refund.

Validate transaction_id uniqueness and deduplication, currency/value consistency, items IDs and quantities, and test through GTM Preview plus GA4 DebugView. Do not add tagging to existing notebook reports or fire fake purchase events from the NEXUS portfolio.

## Release acceptance

1. Offline tests verify GA4, GSC and PageSpeed parsing plus date/url validation.
2. Actual access for each property is checked independently; service credentials are never committed.
3. Daily GA4/GSC report totals are verified against their own Google UI under matching settings, with discrepancies documented.
4. Real mobile and desktop PageSpeed audits are captured, with timestamps. CrUX is required before presenting field Web Vitals.
5. BigQuery models must have data freshness, grain, uniqueness and null checks before joining verified sources.
6. Power BI and/or Looker Studio pages display source labels, periods, coverage warnings and unknown values clearly.

## Google documentation

- GA4 Data API: https://developers.google.com/analytics/devguides/reporting/data/v1/basics
- GA4 BigQuery export: https://support.google.com/analytics/answer/7029846?hl=en
- GSC Search Analytics: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- GSC BigQuery bulk export: https://developers.google.com/search/blog/2023/02/bulk-data-export
- GTM GA4 e-commerce events: https://developers.google.com/tag-platform/gtagjs/reference/events
- Ads API reporting: https://developers.google.com/google-ads/api/docs/reporting/overview
- PSI API: https://developers.google.com/speed/docs/insights/v5/get-started
