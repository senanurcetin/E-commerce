# 17 October 2026 — BigQuery source inventory evidence

Metadata-only discovery supplied by the repository owner: BigQuery
`datasets.list` + `tables.list` collected 2026-10-17 10:18:09 UTC.
No SQL, table schemas, rows, finance reconciliation or freshness checks were
performed. Do not publish this as verified revenue.

## Observed source contracts

| Domain | Exact source | Required tables visible | Outcome |
|---|---|---:|---|
| E-Commerce (current dbt default) | `workintech-working.e_ticaret` | 4/4 | Existing source pin has all required table names |
| E-Commerce / TheLook alternative | `data-analiz-490513.thelook_ecommerce` | 4/4 | Separate full candidate; do not join/replace without owner choice and row-level lineage |
| Greenweez Google Sheets (current dbt default) | `workintech-working.fvt_gsheet` | 4/4 | Existing source pin has all required table names |
| Greenweez legacy raw | `workintech-working.gwz_raw_data` | 0/7 | Empty dataset; cannot build raw-source marketing marts |
| Greenweez alternative raw | `data-analiz-490513.gz_raw_data` | 3/7 | Sales, product, shipping only; four ad-platform tables absent |
| Greenweez alternative Sheets | `data-analiz-490513.fvt_gsheet` | 1/4 exact | Table identifiers differ; not interchangeable with current dbt source |
| Greenweez catalog | `data-analiz-490513.green_catalog` | No expected core match | Independent catalog domain, out of scope |

A total of **34 datasets** were enumerated in `workintech-working`;
the listing of tables in six opaque dataset IDs returned **403**. The other
project returned **47 datasets** and no metadata errors. Consequently global
source uniqueness is **not** established. Individual known, fully enumerated
datasets can nonetheless be verified *at exact dataset scope*. The importer
will only offer an isolated, cost-capped preview of the already-configured
`workintech-working.fvt_gsheet` source after checking both original mapping
and inventory files. This is a scoped pin, not an automatic global mapping.

## Source policy / release gates

1. Preserve root E-Commerce dbt default `workintech-working.e_ticaret`. Do
   not aggregate TheLook alternative simultaneously or imply matching rows.
2. Use Greenweez Sheets `fvt_gsheet` mode for finance and blended campaign
   costs. Greenweez raw-source ad-platform marts remain blocked until their
   exact required source tables become available.
3. Preview the Sheets table column contracts, BigQuery jobs authorization
   and estimated scan bytes. Then, if acceptable, execute a bounded local
   import and produce the independent Greenweez mart and NEXUS snapshots.
4. Independently audit currency, refunds, revenue semantics, cost and source
   provenance before releasing actual finance KPIs or any combined executive
   reporting. Separate businesses do not share a summed revenue KPI.
5. Store no original inventory JSON or row exports in GitHub. Original scans
   can mention unrelated owner project resources. The repository contains
   only this task-scoped evidence summary.

Run from repository root after `git pull --ff-only origin main`:

```powershell
python -m scripts.cloud_source_mapping
python -m pip install -r integrations/greenweez/scripts/requirements-bq.txt
python integrations/greenweez/scripts/load_gsheet_from_bigquery.py
```

The source mapping utility may exit with code 1 because global coverage is
incomplete, even though the known Sheets source is eligible for **scoped
preview**. The final command is a BigQuery query *dry run* and does **not**
download rows. Only a subsequent explicit `--execute` imports data. Real
query cost/permissions, live schemas and the resulting Power BI refresh have
not been verified in this conversation.


## Prepublication row integrity and minimal source projection

The safe BigQuery loader now selects only required dbt fields, rejecting other
Fivetran/customer columns. During an authorized `--execute` read, it blocks
duplicate or BIGINT-invalid order identifiers, invalid dates, nonfinite amounts
and duplicate daily ad-cost rows **before** replacing the existing DuckDB.
Observed zeros and negative amounts are counted, never silently removed.
A private, aggregate-only `import_audit.source_quality` JSON record is
stored inside the same staged DuckDB as the finance source tables, including
period coverage and missing order-side shipping/refund links. These are
technical checks, not financial certification or evidence of live execution.
