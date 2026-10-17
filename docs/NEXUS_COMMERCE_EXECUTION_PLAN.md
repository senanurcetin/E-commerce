# NEXUS Commerce Intelligence — staged execution and release acceptance

**Snapshot:** 17 October 2026. Canonical repo:
`senanurcetin/nexus-commerce-intelligence`.
**Delivery status:** offline CI previously 5/5 green; real BigQuery,
GA4/GSC properties and Power BI Desktop evidence not yet accepted.

## P0 — GitHub OIDC and pinned BigQuery source gate (BLOCKING)

- [x] WorkinTech `nexus-gha` pool, `nexus-github-main` provider, `nexus-bq-readonly`
  service account and repository 1217831974 impersonation binding
  confirmed by the user from the Google Cloud UI.
- [x] Add manual main-branch-only GitHub Actions OIDC workflow and
  no-row constant query dry-run; add strict pinned-source required-column
  comparisons. Run all offline tests before merge.
- [ ] Grant minimum `bigquery.jobUser` project IAM and dataset-specific
  BigQuery Metadata Viewer for `e_ticaret` and `fvt_gsheet`.
- [ ] Configure GitHub `bigquery-readonly` environment (main-only) plus
  `GCP_WIF_PROVIDER`, `GCP_BQ_SERVICE_ACCOUNT`,
  `GCP_BQ_BILLING_PROJECT` variables.
- [ ] Manually run `BigQuery OIDC metadata connection` and save its
  successful GitHub run URL. Verify 8 exact tables / required columns /
  location / zero scanned or extracted business rows.

**Acceptance:** real WIF authentication + 8/8 pinned table schemas PASS;
offline-only CI does not close this stage. **Owner dependency:** project/dataset
IAM and GitHub Settings access.

## P1 — Controlled Greenweez and E-Commerce source preflight (BLOCKING)

- [ ] Verify a fresh, authorized metadata mapping before live source queries.
- [ ] Run bounded four-query Greenweez `--execute`-OFF schema/cost dry-run.
- [ ] Run independent E-Commerce four-table schema/cost dry-run.
- [ ] Preserve provenance and immutable non-sensitive receipts under
  gitignored `target/cloud_inventory/`; do not upload tokens or raw rows.
- [ ] Approve source-row access with dataset-scoped BigQuery Data Viewer only
  after the query limit and data-owner authorization are checked.

**Acceptance:** source-specific, schema/cost bounded receipts with source
IDs, date and region, zero downloaded source rows at preflight stage.

## P2 — Source extraction, dbt and finance reconciliation (BLOCKING)

- [ ] With explicit authorization, import only Greenweez selected columns
  to a local private DuckDB; retain atomic rollback and row/byte caps.
- [ ] Validate 4 source tables, order ID uniqueness, completeness, date
  windows, refund/shipping linkage, missing turnover, negative/zero values.
- [ ] Build `source_system: fvt_gsheet` independent dbt models on actual
  authorized source; compare daily/monthly outputs to source evidence.
- [ ] Independently verify `workintech-working.e_ticaret` historical marts.
- [ ] Do not merge `data-analiz-490513.thelook_ecommerce` with the Workintech
  source or claim actual CAC/ROAS until provenance and revenue are reconciled.

**Acceptance:** reproducible real-source QA and documented financial
definitions from data owners; `external_unverified` remains until confirmed.

## P3 — Source-isolated NEXUS Streamlit and Google measurement acceptance

- [x] Existing Streamlit AppTest covers missing/invalid/synthetic source
  scenarios and source switching; NEXUS logo/theme present.
- [ ] Real-data dashboard smoke, responsive browser/a11y acceptance.
- [ ] GA4 Data API: obtain numeric property ID and read-only authorization.
- [ ] GSC: verify exact Search Console property before export.
- [ ] Show independent source age, consent and source-type qualifications;
  no fabrication of any missing KPI or joined cross-merchant turnover.

**Acceptance:** verified property identities and real browser QA, with
synthetic and missing source states visibly distinct from real sources.

## P4 — Power BI Desktop acceptance (BLOCKING)

- [x] Seven-page NEXUS PBIP/PBIR/TMDL generator and static field-binding QA.
- [ ] Generate report from correctly labelled source-validated aggregates.
- [ ] Open and refresh all seven pages in licensed Windows Power BI Desktop.
- [ ] Check DAX semantics, source isolation, visuals, slicers, branding,
  layout at desktop/mobile widths, and screenshot audit trail.

**Acceptance:** independent Desktop evidence; static PBIP PASS is insufficient.

## P5 — Repository, CI and operational hardening

- [x] Canonical repository rename and Greenweez source subtree integration.
- [x] Five offline CI jobs; all offline tests keep data/source truth isolated.
- [ ] Confirm legacy Greenweez repo status and historical backup need.
- [ ] Confirm external URLs, CircleCI/Vercel integrations and branch rules.
- [ ] Update public README/repo description and release docs to avoid
  overstating actual GCP/GA4/Power BI production verification.
- [ ] Perform cost/permission/privacy review and explicit release approval.

**Acceptance:** no leaked credentials/source rows, main CI green,
outstanding product/third-party acceptance clearly recorded.

## P6 — Release

**Status: HOLD.** Publish a business-validated release only after P0–P5
blocking controls are demonstrably accepted. The release candidate may
remain code-complete with independently labelled synthetic demo capability.

Tracking: GitHub Issues #48 (live data and Power BI) and #58 (migration).
