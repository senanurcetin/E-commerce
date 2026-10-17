# NEXUS Commerce Intelligence — Power BI visual and Desktop release gates

## Source of truth

- **Data/model source:** repository dbt models, tests, Jinja macros and `analyses/` SQL, with BigQuery as the historical warehouse and DuckDB for reproducible local checks.
- **Power BI evidence:** three **historical screenshots** under `docs/assets/`, [DAX measure documentation](dax-measures.md), and the [importable JSON theme](../powerbi/themes/nexus-commerce.json).
- **Generated source, Desktop acceptance pending:** the repository now includes a reproducible **seven-page native PBIP generator** (not a committed PBIX report); its output is created locally under the gitignored `target/powerbi/project/`. CI checks structural integrity and source isolation, **not** Microsoft Power BI Desktop rendering, model refresh, licenses or source-accounted finance. See [PBIP pipeline](../powerbi/PBIP_PIPELINE.md).
- **Separate dataset:** the Olist notebooks are public dataset analysis, not the clickstream/order mart backing the three Power BI screenshots. Do not combine their results in one dashboard caption.

## Existing images (repository assets, not fresh report validation)

| Page | PNG | Tracked size |
| --- | --- | ---: |
| Channel Acquisition Efficiency | [powerbi-channel-performance.png](assets/powerbi-channel-performance.png) | 347,816 bytes |
| Signups and Basket Value | [powerbi-traffic-trend.png](assets/powerbi-traffic-trend.png) | 781,854 bytes |
| Demographics and Customer Type | [powerbi-demographics.png](assets/powerbi-demographics.png) | 567,435 bytes |

File presence, dimensions and chart labels must be checked against an actual report render before calling these current. The screenshots have not been replaced in this documentation/theme change. The larger files warrant a **visually reviewed** compression plan if they are later reused on a public website, not automatic quality-reducing conversion.

## Semantic acceptance checks

1. **Acquisition versus sessions:** `dim_user.signup_traffic_source` (search/organic/facebook/email/display) records user signup attribution; `fct_marketing_web_performance.traffic_source` (email/adwords/youtube/facebook/organic) records individual session attribution. Never label these as the same channel variable.
2. **Denominators:** ensure user counts, distinct customers, session counts, conversions and order-item revenue use their intended grains. Preserve filters and data-type semantics across the two facts.
3. **Conversion ranking:** [`analyses/channel_conversion_significance.sql`](../analyses/channel_conversion_significance.sql) documents a historical five-source chi-square result `χ² = 6.73` (df=4, p≈0.15); do not claim significant session-source conversion differences without a new run on the current data.
4. **PE4 efficiency score:** [DAX documentation](dax-measures.md) weights conversion/revenue/session-count proxies. There is **no observed marketing spend or true customer-acquisition cost** in this calculation; do not label its CAC proxy as actual cost.
5. **Units and date coverage:** Turkish **B** means *bin* (thousand), not billion. The historical report describes 2026 as a partial year; apparent declines must not be read without period alignment.
6. **Returns / net revenue:** reconcile the sign and grain of `revenue` and `returned_revenue` in the marts before presenting return rates, margin or financial performance as current.

## Power BI Desktop acceptance checklist — not completed here

- [x] Generate the seven-page PBIP from local source-scoped aggregate-only inputs and run `python -m scripts.powerbi_structure_audit --out target/powerbi` in CI; results are *structural* only.
- [ ] Open the generated PBIP in **Power BI Desktop**, verify the registered NEXUS theme and original logo, save a versioned copy, and confirm import compatibility.
- [ ] Refresh the model from an authorized data source and record successful/failed queries; verify calendar relationships and measure filter contexts.
- [ ] Inspect **all seven generated pages** at desktop and mobile widths: source status, historical E-Commerce, sessions, Greenweez finance, source quality, import evidence and Commerce Lab. Check titles, card axes, legends, format strings, slicers, tooltips and interactions.
- [ ] Separately inspect the three **historical screenshot** pages; they are not screenshots of the new seven-page report.
- [ ] Run/reconcile SQL and DAX spot checks for core metrics: signups, conversions, session count, order revenue, average basket, returns and PE4 rankings.
- [ ] Verify source/attribution semantics and ensure there is no mixing of Olist notebook figures with the main mart.
- [ ] Re-capture genuine PNGs and record the Power BI report version, data refresh date and screenshot date.
- [ ] Confirm the repository README, portfolio card and Social Preview label the version and source honestly.

**Current release decision: HOLD.** Offline CI now proves that seven generated PBIP pages have declared model bindings and isolated aggregate CSV inputs. It does NOT establish Desktop rendering, source refresh, human visual acceptance, currency units, refunds or independently verified finance. Existing historical PNGs remain archival evidence.
