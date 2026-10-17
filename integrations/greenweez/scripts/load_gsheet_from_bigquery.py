"""Safe, source-qualified BigQuery -> local Greenweez Sheets DuckDB import.

Uses an exact, owner-scoped Sheets source confirmed by metadata table contract.
An incomplete global inventory is allowed only for the pinned existing source
and only if the independently supplied inventory corroborates the mapping.
Default is a zero-row dry-run of four BigQuery SELECT statements (may require
BigQuery jobs.create). Only --execute downloads data and publishes a local file.
Do not commit output data or print credentials/order IDs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess

OWNER_ROOT = Path(__file__).resolve().parents[3]
GREENWEEZ_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = OWNER_ROOT / "target/cloud_inventory/source_mapping_candidates.json"
DEFAULT_INVENTORY = OWNER_ROOT / "target/cloud_inventory/bq_source_locations.json"
# Existing dbt source pin, explicitly chosen for this E-Commerce workspace.
# Do not infer a canonical source from the unrelated project with overlapping tables.
SCOPED_SHEETS_SOURCE = ("workintech-working", "fvt_gsheet")
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


def check_inventory_evidence(inventory: dict, project: str, dataset: str, report: dict) -> None:
    """Verify the exact known dataset against the separate, read-only metadata export.

    This verifies table *names*, not data semantics or global source uniqueness.
    Access-denied unrelated datasets never become negative/positive evidence.
    """
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise ValueError("Missing or unsupported BigQuery inventory")
    if (not inventory.get("scanned_at_utc")
            or inventory.get("scanned_at_utc") != report.get("inventory_scanned_at_utc")):
        raise ValueError("Mapping and inventory refer to different scans")
    projects = inventory.get("results")
    if not isinstance(projects, list) or len(projects) != len(ALLOWED_PROJECTS):
        raise ValueError("Unexpected project count in BigQuery inventory")
    seen = set()
    chosen = None
    for item in projects:
        if not isinstance(item, dict) or item.get("project") not in ALLOWED_PROJECTS:
            raise ValueError("Unexpected project in BigQuery inventory")
        name = item["project"]
        if name in seen:
            raise ValueError("Duplicate project in BigQuery inventory")
        seen.add(name)
        if item.get("status") != "listed" or not isinstance(item.get("datasets"), list):
            raise ValueError("Target inventory cannot be independently reviewed")
        if name == project:
            matches = [x for x in item["datasets"]
                       if isinstance(x, dict) and x.get("dataset") == dataset]
            if len(matches) != 1:
                raise ValueError("Exact pinned BigQuery dataset not listed once")
            chosen = matches[0]
    if chosen is None or chosen.get("status") != "listed":
        raise ValueError("Pinned dataset table metadata unavailable")
    match = chosen.get("matches", {}).get("greenweez_gsheet")
    if (not isinstance(match, dict)
            or set(match.get("found", [])) != set(TABLES)
            or match.get("all_required_tables_present") is not True
            or match.get("expected") != len(TABLES)):
        raise ValueError("Pinned source does not contain all expected Greenweez Sheets tables")


def checked_source(report: dict, inventory: dict | None = None) -> tuple[str, str]:
    """Resolve the selected source; global uniqueness and scoped pin are distinct."""
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("Missing or unsupported source mapping")
    item = report.get("sources", {}).get("greenweez_gsheet")
    if not isinstance(item, dict):
        raise ValueError("Greenweez Sheets mapping absent")
    candidates = item.get("complete_candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise ValueError("Expected exactly one selected full Sheets source")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ValueError("Invalid Sheets mapping candidate")
    project, dataset = candidate.get("project"), candidate.get("dataset")
    if (not isinstance(project, str) or project not in ALLOWED_PROJECTS
            or not PROJECT_ID.fullmatch(project)
            or not isinstance(dataset, str) or not DATASET_ID.fullmatch(dataset)):
        raise ValueError("Invalid or unapproved source project/dataset")
    if set(item.get("required_tables", [])) != set(TABLES):
        raise ValueError("Incomplete or unexpected Sheets source table contract")

    if report.get("inventory_complete") is True:
        if item.get("status") != "ready_for_manual_review":
            raise ValueError("Complete inventory has no uniquely confirmed Sheets source")
        values = item.get("suggested_dbt_vars")
        if not isinstance(values, dict) or values != {
            "greenweez_gsheet_project": project,
            "greenweez_gsheet_dataset": dataset,
        }:
            raise ValueError("Candidate does not agree with dbt source mapping")
    else:
        if item.get("status") != "inventory_incomplete":
            raise ValueError("Source inventory incomplete: partial source status unexpected")
        if (project, dataset) != SCOPED_SHEETS_SOURCE:
            raise ValueError("Partial inventory can only preview the explicitly pinned existing Sheets source")
        if inventory is None:
            raise ValueError("Partial inventory requires the original corroborating BigQuery inventory")

    if inventory is not None:
        check_inventory_evidence(inventory, project, dataset, report)
    return project, dataset

def table_sql(project: str, dataset: str, table: str, max_rows: int) -> str:
    if (project not in ALLOWED_PROJECTS or not PROJECT_ID.fullmatch(project)
            or not DATASET_ID.fullmatch(dataset) or table not in TABLES
            or not isinstance(max_rows, int) or not 1 <= max_rows <= 1000000):
        raise ValueError("Invalid source identifier or row cap")
    fields = ", ".join(chr(96) + name + chr(96) for name in sorted(TABLES[table]))
    identifier = chr(96) + f"{project}.{dataset}.{table}" + chr(96)
    return f"SELECT {fields} FROM {identifier} LIMIT {max_rows + 1}"


# Actual finance identifiers are never emitted in audit results or exceptions.
ROW_CONTRACTS = {
    "gwz_finance_orders_orders": ("orders_id", "datetime", ("turnover", "purchase_cost", "ship_fee")),
    "gwz_finance_shipping_shipping": ("orders_id", "date_date", ("log_cost", "ship_cost")),
    "gwz_finance_refund_sheet_1": ("orders_id", "datetime", ("refund",)),
    "gwz_finance_campaign": (None, "datetime", ("cost",)),
}


def _order_key(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    raw = str(value).strip()
    if not re.fullmatch(r"[0-9]+(?:\.0+)?", raw):
        return None
    digits = raw.split(".", 1)[0].lstrip("0") or "0"
    return digits if int(digits) <= 2**63 - 1 else None


def validate_import_frame(table: str, frame) -> dict:
    """Fail before publishing bad data; report ONLY counts and date ranges."""
    import pandas as pd
    if table not in TABLES or set(frame.columns) != TABLES[table] or frame.empty:
        raise ValueError(f"{table}: invalid projection or empty source")
    key, date_col, numeric_cols = ROW_CONTRACTS[table]
    if key is not None:
        keys = frame[key].map(_order_key)
        invalid = int(keys.isna().sum())
        duplicate = int(keys.dropna().duplicated().sum())
        if invalid or duplicate:
            raise ValueError(f"{table}: invalid order identifiers {invalid}; duplicates {duplicate}")
    dates = pd.to_datetime(frame[date_col].astype(str).str[:10],
                           format="%Y-%m-%d", errors="coerce", utc=True)
    if dates.isna().any():
        raise ValueError(f"{table}: unparseable source calendar dates")
    if key is None and dates.duplicated().any():
        raise ValueError(f"{table}: duplicate campaign day")
    summary = {
        "rows": len(frame),
        "start_date": dates.min().date().isoformat(),
        "end_date": dates.max().date().isoformat(),
        "negative_count": {},
        "zero_count": {},
    }
    for name in numeric_cols:
        numbers = pd.to_numeric(frame[name], errors="coerce")
        if not numbers.map(lambda v: pd.notna(v) and math.isfinite(float(v))).all():
            raise ValueError(f"{table}: invalid or nonfinite amount in {name}")
        summary["negative_count"][name] = int((numbers < 0).sum())
        summary["zero_count"][name] = int((numbers == 0).sum())
    return summary


def audit_join_coverage(con) -> dict:
    """Counts only; does not expose raw order identifiers."""
    output = {}
    for label, other in (
        ("shipping", "gwz_finance_shipping_shipping"),
        ("refund", "gwz_finance_refund_sheet_1"),
    ):
        missing = con.execute(
            "SELECT COUNT(*) FROM analytics.gwz_finance_orders_orders AS o "
            f"LEFT JOIN analytics.{other} AS x "
            "ON CAST(o.orders_id AS BIGINT) = CAST(x.orders_id AS BIGINT) "
            "WHERE x.orders_id IS NULL"
        ).fetchone()[0]
        output["orders_without_" + label] = int(missing)
    return output


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
    quality = {}
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
            quality[table] = validate_import_frame(table, frame)
            for col in frame.columns:
                if str(frame[col].dtype) == "dbdate":
                    frame[col] = pd.to_datetime(frame[col].astype(str)).dt.date
            con.register("source_frame", frame)
            try:
                con.sql(f"CREATE TABLE analytics.{table} AS SELECT * FROM source_frame")
            finally:
                con.unregister("source_frame")
            counts[table] = len(frame)
        audit = {
            "schema_version": 1,
            "source_project": project,
            "source_dataset": dataset,
            "provenance": "external_unverified",
            "financial_semantics_verified": False,
            "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
            "tables": quality,
            "join_coverage": audit_join_coverage(con),
        }
        con.execute("CREATE SCHEMA import_audit")
        con.execute("CREATE TABLE import_audit.source_quality(report JSON)")
        con.execute("INSERT INTO import_audit.source_quality VALUES (?)",
                    [json.dumps(audit, allow_nan=False)])
        con.close()
        con = None
        os.replace(temp, output)
    finally:
        if con is not None:
            con.close()
        if temp.exists():
            temp.unlink()
    return {"row_counts": counts, "quality_audit": audit}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
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
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        project, dataset = checked_source(mapping, inventory=inventory)
        if mapping.get("inventory_complete") is not True:
            print("SCOPED PREVIEW ONLY: other BigQuery datasets inaccessible;",
                  "the existing Sheets source has a complete table-name contract.")
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
            outcome = transfer(client, bigquery, project, dataset, location,
                               output=args.output, cap=args.max_bytes_billed,
                               max_rows=args.max_rows)
        finally:
            client.close()
        print("Published local DuckDB after all four tables succeeded:", args.output)
        print("Rows per source:", ", ".join(f"{k}={v}" for k, v in outcome["row_counts"].items()))
        print("Private aggregate-only import audit saved inside DuckDB: import_audit.source_quality")
        print("Missing order-side relations:", outcome["quality_audit"]["join_coverage"])
        print("Financial semantics/currency still unverified; never commit this local database.")
        return 0
    except (OSError, RuntimeError, ValueError, KeyError, ImportError) as exc:
        # Errors must not contain access tokens or raw query payloads.
        print("BLOCKED:", str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
