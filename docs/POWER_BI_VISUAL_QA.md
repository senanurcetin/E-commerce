# E-commerce Power BI visual QA — evidence and release gate (12 October 2026)

## Source of truth

- **Data/model source:** repository dbt models, tests, Jinja macros and `analyses/` SQL, with BigQuery as the historical warehouse and DuckDB for reproducible local checks.
- **Power BI evidence:** three **historical screenshots** under `docs/assets/`, [DAX measure documentation](dax-measures.md), and the [importable JSON theme](../powerbi/themes/nexus-commerce.json).
- **Missing editable artifact:** the repository does **not** contain a `.pbix` or `.pbip` file. It is not possible to establish that the current report renders, refreshes or uses the new theme solely from these files.
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

- [ ] Import [`nexus-commerce.json`](../powerbi/themes/nexus-commerce.json) into the *original editable report*, save a versioned copy and verify the report still opens.
- [ ] Refresh the model from an authorized data source and record successful/failed queries; verify calendar relationships and measure filter contexts.
- [ ] Inspect the three pages at normal desktop and mobile widths: titles, cards, chart axes, legend readability, outliers, format strings, slicers, tooltips and interactivity.
- [ ] Run/reconcile SQL and DAX spot checks for core metrics: signups, conversions, session count, order revenue, average basket, returns and PE4 rankings.
- [ ] Verify source/attribution semantics and ensure there is no mixing of Olist notebook figures with the main mart.
- [ ] Re-capture genuine PNGs and record the Power BI report version, data refresh date and screenshot date.
- [ ] Confirm the repository README, portfolio card and Social Preview label the version and source honestly.

**Current release decision:** HOLD. A JSON theme update, existing PNG screenshots, and dbt/SQL test code cannot prove Power BI Desktop visuals or current live data are valid. No production data or report file was modified in this PR.
