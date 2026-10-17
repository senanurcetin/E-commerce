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