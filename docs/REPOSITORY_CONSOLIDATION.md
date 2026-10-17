# NEXUS Commerce Intelligence — repository consolidation

## Canonical name and current state

| Item | Value |
| --- | --- |
| Product | **NEXUS Commerce Intelligence** |
| Target GitHub repository | **senanurcetin/nexus-commerce-intelligence** |
| Current live GitHub repository | **senanurcetin/nexus-commerce-intelligence** (rename independently confirmed via GitHub API) |
| Standalone repository scheduled for deletion | **senanurcetin/greenweez-finance-campaign-analytics** |
| Maintained Greenweez source | [integrations/greenweez/](../integrations/greenweez/README.md) |
| Active CI | [Root GitHub Actions CI](../.github/workflows/ci.yml) |
| GitHub administration | **RENAME CONFIRMED; standalone Greenweez URL currently inaccessible (404), deletion not independently proven** |

The GitHub main repository name `nexus-commerce-intelligence` is now live.
The previous `E-commerce` API path returns a redirect. The former standalone
Greenweez repository returned GitHub **404** when checked, but a 404 is not
independent evidence of irreversible deletion (private/restricted visibility
can also cause 404). Keep administrator confirmation and external link reviews
open until verified. The connector does not support destructive repo deletion.

## Before deleting the standalone Greenweez repository

The standalone Greenweez main branch was compared against the integrated
subtree on 17 October 2026:

| Control | Verified result |
| --- | --- |
| Standalone source files | 80 |
| Corresponding integrated paths under integrations/greenweez | **80 / 80** |
| Exact identical Git blobs | 76 |
| Intentional integrated changes | 4 |
| Missing upstream-only paths | **0** |

The intentionally changed paths are Makefile,
models/staging/schema.yml, models/staging/gsheet/schema.yml, and
scripts/load_gsheet_from_bigquery.py. The integrated versions add safer
source-variable configuration, pinned source selection, bounded dry-runs,
explicit authorization for row reads, atomic DuckDB publication, and
privacy-safe quality evidence. **Do not overwrite them with the standalone
versions.**

The Greenweez source was originally copied through a **squashed Git subtree**.
This preserves the current source files, not necessarily the historical
standalone Git commits, branches, closed issues, pull requests, workflow
artifacts, or releases. GitHub deletion can permanently remove that
repository-specific history. If any of it is valuable, preserve a mirror or
bundle and export relevant issues/PRs *before* deletion.

## Required GitHub administrator actions

1. **Rename: COMPLETED.** The GitHub API now resolves the full repository
   `senanurcetin/nexus-commerce-intelligence`; original `E-commerce`
   repository API URLs return a redirect. Existing PRs and issues are visible.
2. **Update Git remotes.** In the local Windows checkout run:

   ~~~powershell
   git remote set-url origin https://github.com/senanurcetin/nexus-commerce-intelligence.git
   git remote -v
   git pull --ff-only origin main
   ~~~

   The local folder can remain C:\Users\MONSTER\E-commerce; the folder name
   is independent of the GitHub repository slug.
3. **Verify integrations and deployments.** Check root GitHub Actions and
   CircleCI, Vercel Commerce Lab Git import, portfolio links, branch rules,
   webhooks, badges, any public project URLs and CI/deployment credentials.
   Do not assume all external services follow GitHub redirects.
4. **Verify final source preservation and green CI** on the newly named repo.
   Confirm that integrations/greenweez still contains the 80 source paths.
5. **Confirm old standalone Greenweez repository state.** The old URL
   currently returns 404. Confirm with an authorized repository administrator
   that it was actually deleted (rather than made private), and whether its
   historical issues/branches/PR records were backed up if necessary.
6. **Verify deletion and external links.** After deletion, standalone
   Greenweez repository URLs will no longer work. All active project docs
   should refer to the internal integrations/greenweez subtree. The
   consolidated repo is the sole maintained source of project changes.

## Data products remain deliberately separated

One GitHub repository does **not** mean one joined business dataset:
historical E-Commerce (workintech-working.e_ticaret), Greenweez Sheets
(workintech-working.fvt_gsheet), Commerce Lab test events, GA4, GSC and
Olist remain isolated. TheLook alternative data-analiz-490513.thelook_ecommerce
must not be automatically unioned. Greenweez raw advertising tables are
incomplete in data-analiz-490513.gz_raw_data.

GitHub CI only proves deterministic test and build contracts. Real BigQuery
authorization, source row quality, finance currency/refund reconciliation and
Power BI Desktop render/refresh remain external release gates (**HOLD**).
