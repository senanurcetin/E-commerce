# Locate E-Commerce and Greenweez in the owner's two GCP projects

The two projects are `workintech-working` and `data-analiz-490513`.
Previous BigQuery inventory listed 34 datasets in `data-analiz-490513`, including candidate Greenweez dataset names `gz_raw_data` and `fvt_gsheet`; actual live table membership was not established.

## Why the unified report currently has empty marts

| Business domain | Repo dbt location | Required source tables |
|---|---|---|
| E-Commerce | `workintech-working.e_ticaret` | `events`, `order_items`, `products`, `users` |
| Greenweez raw | `workintech-working.gwz_raw_data` | `raw_gz_sales`, `raw_gz_product`, `raw_gz_ship`, `raw_gz_adwords`, `raw_gz_bing`, `raw_gz_criterio`, `raw_gz_facebook` |
| Greenweez Fivetran/Sheets | `workintech-working.fvt_gsheet` | `gwz_finance_orders_orders`, `gwz_finance_shipping_shipping`, `gwz_finance_refund_sheet_1`, `gwz_finance_campaign` |

The source code assumes `workintech-working`; this is a **configuration**, not proof tables still exist there. The other project's historical inventory pointed at `gz_raw_data`, whereas the dbt source uses `gwz_raw_data` (different exact names). Do not change the mapping, merge rows, grant permissions, or copy warehouse datasets before verifying.

## Run read-only metadata inventory

From the user's Windows PowerShell with existing `gcloud auth login`:

```powershell
cd C:\Users\MONSTER\E-commerce
git switch main
git pull --ff-only origin main
python -m scripts.cloud_source_inventory
```

The tool calls **only** `projects/*/datasets` and `projects/*/datasets/*/tables` metadata endpoints in BigQuery REST; it makes **no SQL**, `jobs.query`, `SELECT *`, data row reads, mutations, user credential persistence, or cloud writes. Outputs a human-readable summary plus a metadata-only JSON inventory at `target/cloud_inventory/bq_source_locations.json` (gitignored). The only authentication is an existing local `gcloud auth login` account; no private-key JSON required.

If no datasets are visible due to permissions, output explicitly says `access_denied_or_unavailable`; this must never be interpreted as the project having no data. In that case have a project IAM administrator review *metadata viewing* rights; do not use the GA4 service account's Analytics Viewer role as though it granted BigQuery access.

After inventory returns known table coverage, use that evidence to configure the dbt BigQuery source `database:` and `schema:` properties, and separately validate data freshness, currency, costs and finance definitions before generating final business KPI marts. E-Commerce/TheLook vs Greenweez must remain separate business domains.

Current dashboard/Power BI uses source-gated local snapshots. Finding a BigQuery dataset does **not** automatically populate `target/ecommerce_bridge/snapshot.json` or `target/greenweez_bridge/snapshot.json`.
## Confirmed-source runtime overrides (no warehouse migration)

This repository keeps the existing defaults until the **live** inventory proves the actual location of every required table. BigQuery source addresses are now configurable through dbt `--vars`, independently for the root E-Commerce project and the integrated Greenweez project. This changes only how dbt resolves **source relations**; it does not copy or alter warehouse data.

1. Run `python -m scripts.cloud_source_inventory` on a machine authenticated to both GCP projects. Inspect `target/cloud_inventory/bq_source_locations.json`.
2. Run `python -m scripts.cloud_source_mapping`. The reconciler writes `target/cloud_inventory/source_mapping_candidates.json` and refuses to mark a mapping ready if **any** dataset/table listing is inaccessible, an exact set of required tables is missing, or multiple full candidates exist.
3. Apply **only uniquely confirmed** project/dataset values in the corresponding dbt command below. Do not infer a mapping from similar dataset names (notably `gz_raw_data` versus `gwz_raw_data`).

Root E-Commerce (illustrative placeholders; replace only with verified inventory values):

```sh
dbt parse --profiles-dir .github/dbt-profiles --vars '{"ecommerce_source_project":"<verified-project>","ecommerce_source_dataset":"<verified-dataset>"}'
```

Greenweez (the raw and sheet source projects/datasets can differ):

```sh
cd integrations/greenweez
dbt parse --profiles-dir .github/dbt-profiles --target ci --vars '{"greenweez_raw_project":"<verified-raw-project>","greenweez_raw_dataset":"<verified-raw-dataset>","greenweez_gsheet_project":"<verified-sheet-project>","greenweez_gsheet_dataset":"<verified-sheet-dataset>"}'
```

The current defaults remain: E-Commerce `workintech-working.e_ticaret`, Greenweez raw `workintech-working.gwz_raw_data`, and Greenweez sheets `workintech-working.fvt_gsheet`. These are **unverified defaults**, not evidence of active data. `dbt parse` is an offline configuration check, not a source query or proof of table access. Live BigQuery testing and downstream marts must wait for a verified, authorized warehouse connection. Greenweez DuckDB CI/demo targets keep their existing synthetic-seed routing.


## Greenweez real Fivetran/Sheets import: controlled local handoff

The legacy script previously deleted its existing DuckDB before querying BigQuery.
It now requires a **unique, complete** metadata mapping, validates actual source
table schemas, performs four **BigQuery dry-run jobs**, and leaves the old local DB
unchanged unless every source completes successfully. No service-account key file
is needed: it uses the existing signed-in \`gcloud auth login\` user and an
in-memory short-lived access token.

From the E-Commerce root on Windows, run these only **after** the two metadata
inventory commands above have finished:

\`\`\`powershell
python -m pip install -r integrations/greenweez/scripts/requirements-bq.txt
python integrations/greenweez/scripts/load_gsheet_from_bigquery.py
\`\`\`

This default **preview** calls BigQuery metadata and query dry-run endpoints but
**downloads no data** and does not change \`gsheet_real.duckdb\`. A query job
permission can still be required. The source project/dataset is derived from
the local \`source_mapping_candidates.json\`, never guessed from a similar name.
If source location differs from the query-billing project, explicitly pass
\`--billing-project workintech-working\` (requires BigQuery jobs.create there).

Once the preview shows four verified column sets and acceptable bytes, authorize
the real read by running:

\`\`\`powershell
python integrations/greenweez/scripts/load_gsheet_from_bigquery.py --execute
\`\`\`

The default per-query billing ceiling is **50,000,000 bytes**, and the default
row ceiling is 250,000 per table. These are guards, *not* a guarantee of a
zero-cost operation. The resulting real-data file is gitignored at
\`integrations/greenweez/target/gsheet_real.duckdb\`; never commit/share it.
If \`gcloud\` access only permits metadata, the preview will stop and report the
authorization blocker; it will not silently substitute demo rows.

After this local import, enter \`integrations/greenweez\` and run:

\`\`\`powershell
dbt deps --profiles-dir .github/dbt-profiles
dbt build --profiles-dir .github/dbt-profiles --target gsheet_real --vars "{source_system: fvt_gsheet}" --selector fvt_gsheet --indirect-selection cautious --exclude resource_type:seed
\`\`\`

Only after reviewing this real-but-uncertified mart should it be sent through
the NEXUS source-qualified bridge, with provenance \`external_unverified\`.
Do **not** promote source order turnover, refund figures or ad spend to certified
financial KPIs until units, currency and business semantics reconcile.
