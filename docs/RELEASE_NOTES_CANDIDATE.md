# NEXUS Commerce Intelligence — release candidate (not published)

**Status: HOLD.** This is a source-controlled milestone description, not a release tag, GitHub Release, real business certification or Power BI Desktop acceptance.

## Included code and product modules

- Historical E-Commerce three-layer dbt marts for events/orders and Olist notebooks kept separate.
- Complete isolated Greenweez dbt subproject under `integrations/greenweez/`, including the safe Sheets loader and quality gates.
- One source-scoped NEXUS Streamlit dashboard, Greenweez source evidence and Commerce Lab test-only storefront.
- Seven-page generated native PBIP/PBIR/TMDL with official NEXUS theme/logo and no cross-merchant total measures.
- Metadata/source-scoped BigQuery preflight utilities; all real cloud use explicitly opt-in.
- Five GitHub CI jobs: historical dbt, Greenweez dbt, dashboard/AppTest, Commerce Lab, and **cross-project offline integration**.
- Credential-free PBIP structure audit for page identity, asset presence, and scoped visual model bindings.

## Evidence boundaries

- All successful CI mart builds use synthetic/offline fixtures; neither Greenweez nor TheLook merchant amounts are independently certified.
- Historical Power BI PNG assets show an older report, not screenshots of the generated seven-page PBIP.
- No actual Power BI Desktop render/refresh acceptance or GA4/GSC property-bound export is asserted.
- Marketing efficiency proxies are not ad spend, actual CAC or verified ROAS.
- Cross-project code integration never combines unrelated merchants' customer/order populations.
- The renamed GitHub repo is `senanurcetin/nexus-commerce-intelligence`; old Greenweez code is maintained inside `integrations/greenweez/`.

## Required before a business-data or BI release

- [x] Both dbt domains build and pass their own source-specific CI suites.
- [x] The offline cross-dbt → NEXUS → PBIP integration job passes without credentials.
- [x] PBIP project structure and seven page bindings are statically checked.
- [ ] Complete BigQuery/source row reconciliation with approved credentials and documented financial semantics.
- [ ] Open generated PBIP in Power BI Desktop and approve actual visuals, refresh, slicers and DAX.
- [ ] Obtain independent business acceptance of turnover, currency, refunds and campaign attribution.
- [ ] Review data rights, real-data sharing rules and an immutable release commit; only then tag/publish.

Related: [README](../README.md), [offline integration](NEXUS_OFFLINE_INTEGRATION_ACCEPTANCE.md), [PBIP pipeline](../powerbi/PBIP_PIPELINE.md) and [Desktop QA](POWER_BI_VISUAL_QA.md).
