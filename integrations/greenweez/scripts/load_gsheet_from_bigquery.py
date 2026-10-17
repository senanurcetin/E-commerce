"""Safe, source-qualified BigQuery -> local Greenweez Sheets DuckDB import.

Runs only after a complete metadata inventory identifies exactly one Sheets dataset.
Default is a zero-row dry-run of four BigQuery SELECT statements (may require
BigQuery jobs.create). Only --execute downloads data and publishes a local file.
Do not commit output data or print credentials/order IDs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

OWNER_ROOT = Path(__file__).resolve().parents[3]
GREENWEEZ_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = OWNER_ROOT / "target/cloud_inventory/source_mapping_candidates.json"
DEFAULT_OUTPUT = GREENWEEZ_ROOT / "target/gsheet_real.duckdb"
ALLOWED_PROJECTS = ("workintech-working", "data-analiz-490513")
TABLES = {
    "gwz_finance_orders_orders": {"orders_id", "datetime", "turnover", "purchase_cost", "ship_fee"},
    "gwz_finance_shipping_shipping": {"orders_id", "date_date", "log_cost", "ship_cost"},
    "gwz_finance_refund_sheet_1": {"orders_id", "datetime", "refund"},
    "gwz_finance_campaign": {"datetime", "cost"},
}
PROJECT_ID = re.compile(r"[a-z][a-z0-9-]{4,62}")
DATASET_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,1023}")


def checked_source(report: dict) -> tuple[str, str]:
    """Refuse partial, fabricated, ambiguous or out-of-scope source mappings."""
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("Missing or unsupported source mapping")
    if report.get("inventory_complete") is not True:
        raise ValueError("Source inventory incomplete: permissions or listing errors")
    item = report.get("sources", {}).get("greenweez_gsheet")
    if not isinstance(item, dict) or item.get("status") != "ready_for_manual_review":
        raise ValueError("Greenweez Sheets source not uniquely discovered")
    candidates = item.get("complete_candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise ValueError("Expected exactly one fully matching Sheets source")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ValueError("Invalid Sheets mapping candidate")
    project, dataset = candidate.get("project"), candidate.get("dataset")
    if (not isinstance(project, str) or project not in ALLOWED_PROJECTS
            or not PROJECT_ID.fullmatch(project)
            or not isinstance(dataset, str) or not DATASET_ID.fullmatch(dataset)):
        raise ValueError("Invalid or unapproved source project/dataset")
    values = item.get("suggested_dbt_vars")
    if not isinstance(values, dict) or values != {
        "greenweez_gsheet_project": project,
        "greenweez_gsheet_dataset": dataset,
    }:
        raise ValueError("Candidate does not agree with dbt source mapping")
    if set(item.get("required_tables", [])) != set(TABLES):
        raise ValueError("Incomplete or unexpected Sheets source table contract")
    return project, dataset


def table_sql(project: str, dataset: str, table: str, max_rows: int) -> str:
    if (project not in ALLOWED_PROJECTS or not PROJECT_ID.fullmatch(project)
            or not DATASET_ID.fullmatch(dataset) or table not in TABLES
            or not isinstance(max_rows, int) or not 1 <= max_rows <= 1000000):
        raise ValueError("Invalid source identifier or row cap")
    return f"SELECT * FROM " + chr(96) + f"{project}.{dataset}.{table}" + chr(96) + f" LIMIT {max_rows + 1}"


def access_token() -> str:
    binary = "gcloud.cmd" if os.name == "nt" else "gcloud"
    try:
        p = subprocess.run([binary, "auth", "print-access-token"],
                           capture_output=True, text=True, timeout=40, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("gcloud command unavailable or timed out") from None
    if p.returncode != 0 or not p.stdout.strip():
        # Never expose CLI stderr; some installations include account details.
        raise RuntimeError("Authorize gcloud auth login for the selected projects")
    return p.stdout.strip()


def preview(client, bigquery, project: str, dataset: str, *, cap: int, max_rows: int) -> tuple[str, dict]:
    """Validate actual table schemas and query-cost ceilings before any row read."""
    ds = client.get_dataset(f"{project}.{dataset}")
    location = ds.location
    plan = {}
    for table, required in TABLES.items():
        metadata = client.get_table(f"{project}.{dataset}.{table}")
        columns = {field.name for field in metadata.schema}
        missing = sorted(required - columns)
        if missing:
            raise ValueError(f"{table}: missing required source columns: {', '.join(missing)}")
        sql = table_sql(project, dataset, table, max_rows)
        dry = client.query(sql, location=location, job_config=bigquery.QueryJobConfig(
            dry_run=True, use_query_cache=False, maximum_bytes_billed=cap,
        ))
        estimated = int(dry.total_bytes_processed or 0)
        if estimated > cap:
            raise ValueError(f"{table}: estimated bytes exceed the per-query cost ceiling")
        plan[table] = {"estimated_bytes_scanned": estimated, "schema_columns": len(columns)}
    return location, plan


def transfer(client, bigquery, project: str, dataset: str, location: str,
             *, output: Path, cap: int, max_rows: int) -> dict:
    """Build to a sibling file, replacing previous DB only after all tables succeed."""
    import duckdb
    import pandas as pd

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".staging")
    if temp.exists():
        # Staging file is exclusively ours; never touch the last published DB here.
        temp.unlink()
    counts = {}
    con = None
    try:
        con = duckdb.connect(str(temp))
        con.sql("CREATE SCHEMA analytics")
        for table in TABLES:
            sql = table_sql(project, dataset, table, max_rows)
            job = client.query(sql, location=location, job_config=bigquery.QueryJobConfig(
                maximum_bytes_billed=cap, use_query_cache=False,
            ))
            frame = job.result().to_dataframe(create_bqstorage_client=False)
            if len(frame) > max_rows:
                raise ValueError(f"{table}: row cap exceeded; no partial snapshot published")
            if len(frame) == 0:
                raise ValueError(f"{table}: empty required source; no snapshot published")
            for col in frame.columns:
                if str(frame[col].dtype) == "dbdate":
                    frame[col] = pd.to_datetime(frame[col].astype(str)).dt.date
            con.register("source_frame", frame)
            try:
                con.sql(f"CREATE TABLE analytics.{table} AS SELECT * FROM source_frame")
            finally:
                con.unregister("source_frame")
            counts[table] = len(frame)
        con.close()
        con = None
        os.replace(temp, output)
    finally:
        if con is not None:
            con.close()
        if temp.exists():
            temp.unlink()
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--billing-project", choices=ALLOWED_PROJECTS)
    parser.add_argument("--max-bytes-billed", type=int, default=50_000_000,
                        help="Hard cap per SELECT query; default 50MB (4 queries)")
    parser.add_argument("--max-rows", type=int, default=250_000,
                        help="No partial snapshots: stop if a source table exceeds this cap")
    parser.add_argument("--execute", action="store_true",
                        help="Explicitly authorize reads and publication; default is dry-run")
    args = parser.parse_args(argv)
    try:
        if args.max_bytes_billed < 1 or not 1 <= args.max_rows <= 1000000:
            raise ValueError("Query byte and row caps must be positive")
        mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
        project, dataset = checked_source(mapping)
        billing = args.billing_project or project
        # Defer all Google imports/authentication until the mapping is validated.
        from google.cloud import bigquery
        from google.oauth2.credentials import Credentials
        client = bigquery.Client(project=billing, credentials=Credentials(token=access_token()))
        try:
            location, plan = preview(client, bigquery, project, dataset,
                                     cap=args.max_bytes_billed, max_rows=args.max_rows)
            print("Read-only preview:", f"{project}.{dataset}", "| billing:", billing,
                  "| region:", location)
            for table, evidence in plan.items():
                print(table + ": estimated scanned bytes =", evidence["estimated_bytes_scanned"])
            if not args.execute:
                print("DRY RUN: no data rows downloaded; existing DuckDB untouched.")
                return 0
            counts = transfer(client, bigquery, project, dataset, location,
                              output=args.output, cap=args.max_bytes_billed,
                              max_rows=args.max_rows)
        finally:
            client.close()
        print("Published local DuckDB after all four tables succeeded:", args.output)
        print("Rows per source:", ", ".join(f"{k}={v}" for k, v in counts.items()))
        print("Financial semantics/currency still unverified; never commit this local database.")
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, ImportError) as exc:
        # Errors must not contain access tokens or raw query payloads.
        print("BLOCKED:", str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
