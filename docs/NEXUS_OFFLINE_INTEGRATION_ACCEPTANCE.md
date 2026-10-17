# NEXUS Commerce Intelligence — offline cross-project acceptance

The new `offline-integration-ci` GitHub Actions job builds BOTH independent dbt projects
using only synthetic seed data. Root historical E-Commerce and nested Greenweez
finance are separately compiled, tested and imported into the NEXUS workspace.

Then `python -m scripts.verify_offline_pipeline --root . --out target/powerbi`
regenerates the native seven-page PBIP and confirms:

- Both source snapshots exist, contain daily data, and carry SYNTHETIC provenance.
- NEXUS Source Assurance reports exactly nine isolated groups.
- E-Commerce orders, sessions and Greenweez daily finance rows arrive in
  source-specific CSVs with matched row counts; no cross-merchant totals.
- The PBIP has seven correctly bound pages with NEXUS logo/theme assets.
- Evidence retains false BigQuery, financial and Power BI Desktop acceptance flags.

This job does not connect to Google, BigQuery, Vercel or a browser. CI PASS is
offline structural/integration evidence only; live finance reconciliation, real
Power BI Desktop rendering and user-facing responsive/browser acceptance remain
independent tasks.
