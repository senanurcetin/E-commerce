"""No-row BigQuery dry-run preflight for pinned historical E-Commerce source.

Validates inventory and four dbt staging table schemas; NEVER downloads rows.
Run: python -m scripts.ecommerce_bigquery_preflight (after gcloud login).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from scripts.cloud_source_readiness import INVENTORY, MAPPING, PINNED, evaluate

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "target/cloud_inventory/ecommerce_live_preflight.json"
SOURCE = PINNED["ecommerce"]
CONTRACT = {
    "events": (
        "id user_id sequence_number session_id created_at ip_address city state "
        "postal_code browser traffic_source uri event_type"
    ).split(),
    "order_items": (
        "id order_id user_id product_id inventory_item_id status created_at "
        "shipped_at delivered_at returned_at sale_price"
    ).split(),
    "products": (
        "id cost retail_price category name brand department sku distribution_center_id"
    ).split(),
    "users": (
        "id first_name last_name email age gender city state country postal_code "
        "street_address latitude longitude traffic_source created_at"
    ).split(),
}
# Only scalar types; field names and source identities are fixed by this script.
NUMERIC_COLUMNS = {
    "events": {"id", "user_id", "sequence_number"},
    "order_items": {"id", "order_id", "user_id", "product_id", "inventory_item_id", "sale_price"},
    "products": {"id", "cost", "retail_price", "distribution_center_id"},
    "users": {"id", "age", "latitude", "longitude"},
}
DATETIME_COLUMNS = {
    "events": {"created_at"},
    "order_items": {"created_at", "shipped_at", "delivered_at", "returned_at"},
    "products": set(),
    "users": {"created_at"},
}
NUMERIC_TYPES = frozenset(("STRING", "INTEGER", "INT64", "FLOAT", "FLOAT64",
                           "NUMERIC", "BIGNUMERIC"))
DATETIME_TYPES = frozenset(("STRING", "DATE", "DATETIME", "TIMESTAMP"))
TEXT_TYPES = frozenset(("STRING",))


def verify_inventory(inventory: dict, mapping: dict) -> None:
    decision = evaluate(inventory, mapping)
    selected = decision["sources"]["ecommerce"]
    if (not selected["table_names_confirmed"]
            or (selected["project"], selected["dataset"]) != SOURCE):
        raise ValueError("Pinned E-Commerce source table contract unavailable")


def sql(table: str) -> str:
    if table not in CONTRACT:
        raise ValueError("Unexpected E-Commerce source table")
    project, dataset = SOURCE
    quoted = chr(96)
    columns = ", ".join(quoted + col + quoted for col in sorted(CONTRACT[table]))
    return f"SELECT {columns} FROM {quoted}{project}.{dataset}.{table}{quoted} LIMIT 1"


def preflight(client, bigquery, *, cap: int = 100_000_000) -> dict:
    if type(cap) is not int or cap < 1:
        raise ValueError("Invalid per-query byte cap")
    project, dataset = SOURCE
    location = client.get_dataset(f"{project}.{dataset}").location
    if not isinstance(location, str) or not location:
        raise ValueError("Missing BigQuery dataset location")
    tables = {}
    for table, required in CONTRACT.items():
        schema = client.get_table(f"{project}.{dataset}.{table}").schema
        by_name = {col.name: col for col in schema}
        missing = set(required) - set(by_name)
        if missing:
            raise ValueError(f"{table}: missing dbt staging columns: {len(missing)}")
        types = {}
        for name in sorted(required):
            col = by_name[name]
            dtype = str(getattr(col, "field_type", "")).upper()
            mode = str(getattr(col, "mode", "NULLABLE")).upper()
            accepted = (NUMERIC_TYPES if name in NUMERIC_COLUMNS[table]
                        else DATETIME_TYPES if name in DATETIME_COLUMNS[table]
                        else TEXT_TYPES)
            if dtype not in accepted or mode == "REPEATED":
                raise ValueError(f"{table}: unsuitable or repeated field {name}")
            types[name] = dtype
        job = client.query(sql(table), location=location,
                           job_config=bigquery.QueryJobConfig(
                               dry_run=True, maximum_bytes_billed=cap,
                               use_query_cache=False))
        scanned = int(job.total_bytes_processed or 0)
        if not 0 <= scanned <= cap:
            raise ValueError(f"{table}: query estimate exceeds cap")
        tables[table] = {
            "required_field_types": types,
            "schema_columns": len(schema),
            "estimated_bytes_scanned": scanned,
        }
    return {
        "schema_version": 1,
        "source_project": project, "source_dataset": dataset,
        "region": location, "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "live_schema_and_cost_dry_run_passed",
        "per_query_maximum_bytes_billed": cap,
        "tables": tables,
        "rows_downloaded": False,
        "historical_marts_reconciled": False,
        "financial_semantics_verified": False,
        "powerbi_desktop_accepted": False,
    }


def token() -> str:
    exe = "gcloud.cmd" if os.name == "nt" else "gcloud"
    try:
        result = subprocess.run([exe, "auth", "print-access-token"],
                                capture_output=True, text=True, timeout=40, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("gcloud unavailable") from None
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("Authorized gcloud login required") from None
    return result.stdout.strip()


def write_receipt(output: Path, result: dict) -> None:
    if result.get("status") != "live_schema_and_cost_dry_run_passed" or (
            result.get("rows_downloaded") is not False):
        raise ValueError("Refusing invalid E-Commerce preflight receipt")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name(output.name + ".staging")
    try:
        stage.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
        os.replace(stage, output)
    finally:
        if stage.exists():
            stage.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--max-bytes-billed", type=int, default=100_000_000)
    args = parser.parse_args(argv)
    try:
        verify_inventory(json.loads(args.inventory.read_text(encoding="utf-8")),
                         json.loads(args.mapping.read_text(encoding="utf-8")))
        if args.max_bytes_billed < 1:
            raise ValueError("Invalid BigQuery query limit")
        from google.cloud import bigquery
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            # GitHub Actions Workload Identity Federation supplies refreshable ADC.
            client = bigquery.Client(project=SOURCE[0])
        else:
            from google.oauth2.credentials import Credentials
            client = bigquery.Client(project=SOURCE[0],
                                     credentials=Credentials(token=token()))
        try:
            result = preflight(client, bigquery, cap=args.max_bytes_billed)
        finally:
            client.close()
        write_receipt(args.output, result)
        print("P3 E-Commerce dry-run: 4/4 tables checked; zero business rows downloaded.")
        print("Local gitignored receipt:", args.output)
        print("Mart/finance reconciliation and Power BI acceptance: HOLD")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, ImportError) as exc:
        print("BLOCKED: E-Commerce preflight unavailable:", str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
