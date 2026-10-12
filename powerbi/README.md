# NEXUS Commerce — Power BI visual theme

This is a **ready-to-import Power BI JSON theme**, aligned with the project's violet/indigo editorial cover in `docs/assets/ecommerce-analytics-cover.svg`.

## Palette and presentation
- Report canvas: `#F7F7FC` or a custom ink-blue header `#15182C`.
- KPI cards: white, subtle border `#E1E5F2`, consistent large measures.
- Primary comparison series: lavender `#A99AFF` and teal `#36C6CB`; amber and coral only for secondary/alert series.
- Slicer region: group by date, acquisition channel, country and segment.
- Remove gradients, thick outlines and excessive decorative blocks from the existing report; preserve working slicers and business logic.

## Import into an existing report
In **Power BI Desktop** open the real report, select **View → Themes → Browse for themes**, select `themes/nexus-commerce.json`, then save and republish the report.

## Screenshot acceptance criteria
Re-capture the real report only *after* importing this theme and reviewing cards, chart contrast and slicer states in Power BI. Use the existing paths below for evidence screenshots:
- `docs/assets/powerbi-channel-performance.png`
- `docs/assets/powerbi-traffic-trend.png`
- `docs/assets/powerbi-demographics.png`

**Source limitation:** This GitHub repository currently stores report screenshots, dbt models and seeds, but no editable Power BI report (`.pbix` or `.pbip`). Adding this theme alone does **not** modify or publish the existing dashboard, nor regenerate those screenshots. The existing screenshots remain authentic historical report captures.
