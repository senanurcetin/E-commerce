"""Read-only, privacy-safe Greenweez source import audit for NEXUS and Power BI.

The audit is generated INSIDE the local Greenweez DuckDB at import time.
No BigQuery calls and no transaction/customer/order identifiers are exported.
Passing this schema check NEVER constitutes financially verified business data.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path

SCHEMA_VERSION = 1
SOURCE_PROJECT = "workintech-working"
SOURCE_DATASET = "fvt_gsheet"
FIELDS = {
    "gwz_finance_orders_orders": ("turnover", "purchase_cost", "ship_fee"),
    "gwz_finance_shipping_shipping": ("log_cost", "ship_cost"),
    "gwz_finance_refund_sheet_1": ("refund",),
    "gwz_finance_campaign": ("cost",),
}
TABLE_COLUMNS = (
    "table_name", "source_project", "source_dataset", "row_count",
    "min_date", "max_date", "zero_amount_values", "negative_amount_values",
    "unmatched_shipping_orders", "unmatched_refund_orders",
    "provenance", "finance_verified",
)


def _count(value: object, *, min_value: int = 0) -> int:
    if type(value) is not int or value < min_value:
        raise ValueError("Invalid Greenweez aggregate count")
    return value


def validate_audit(audit: object) -> dict:
    if not isinstance(audit, dict) or set(audit) != {
        "schema_version", "source_project", "source_dataset",
        "provenance", "financial_semantics_verified", "extracted_at_utc",
        "tables", "join_coverage",
    }:
        raise ValueError("Greenweez import evidence schema rejected")
    if (audit["schema_version"] != SCHEMA_VERSION or
            audit["source_project"] != SOURCE_PROJECT or
            audit["source_dataset"] != SOURCE_DATASET or
            audit["provenance"] != "external_unverified" or
            audit["financial_semantics_verified"] is not False):
        raise ValueError("Greenweez import provenance not accepted")
    try:
        stamp = datetime.fromisoformat(audit["extracted_at_utc"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Invalid Greenweez extraction timestamp") from exc
    if stamp.tzinfo is None or stamp > datetime.now(timezone.utc):
        raise ValueError("Invalid Greenweez extraction date")
    tables = audit["tables"]
    if not isinstance(tables, dict) or set(tables) != set(FIELDS):
        raise ValueError("Incomplete Greenweez import table audit")
    for name, fields in FIELDS.items():
        row = tables[name]
        if not isinstance(row, dict) or set(row) != {
            "rows", "start_date", "end_date", "negative_count", "zero_count",
        }:
            raise ValueError("Greenweez table-level import evidence rejected")
        _count(row["rows"], min_value=1)
        try:
            start = date.fromisoformat(row["start_date"])
            end = date.fromisoformat(row["end_date"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid Greenweez audit date range") from exc
        if start > end:
            raise ValueError("Inverted Greenweez source date range")
        for field in ("negative_count", "zero_count"):
            values = row[field]
            if not isinstance(values, dict) or set(values) != set(fields):
                raise ValueError("Unexpected monetary field in Greenweez audit")
            for count in values.values():
                if _count(count) > row["rows"]:
                    raise ValueError("Greenweez amount count exceeds source rows")
    joins = audit["join_coverage"]
    if not isinstance(joins, dict) or set(joins) != {
        "orders_without_shipping", "orders_without_refund",
    }:
        raise ValueError("Invalid Greenweez join coverage audit")
    orders = tables["gwz_finance_orders_orders"]["rows"]
    for count in joins.values():
        if _count(count) > orders:
            raise ValueError("Greenweez join coverage exceeds source order rows")
    return audit


def load_import_audit(db: Path) -> dict | None:
    """Read one sealed local audit row from DuckDB without touching raw tables."""
    db = Path(db)
    if not db.is_file():
        return None
    import duckdb
    try:
        connection = duckdb.connect(str(db), read_only=True)
        try:
            rows = connection.execute("SELECT report FROM import_audit.source_quality").fetchall()
        finally:
            connection.close()
    except duckdb.Error as exc:
        raise ValueError("Greenweez source audit unavailable or unreadable") from exc
    if len(rows) != 1 or not isinstance(rows[0][0], str):
        raise ValueError("Greenweez import evidence must have exactly one JSON report")
    try:
        record = json.loads(rows[0][0])
    except json.JSONDecodeError as exc:
        raise ValueError("Greenweez import evidence JSON invalid") from exc
    return validate_audit(record)


def reporting_rows(audit: dict) -> list[dict]:
    """Four source-table audit records; no finance amounts or raw identifiers."""
    audit = validate_audit(audit)
    result = []
    joins = audit["join_coverage"]
    for name in sorted(FIELDS):
        record = audit["tables"][name]
        is_orders = name == "gwz_finance_orders_orders"
        result.append({
            "table_name": name,
            "source_project": SOURCE_PROJECT,
            "source_dataset": SOURCE_DATASET,
            "row_count": record["rows"],
            "min_date": record["start_date"],
            "max_date": record["end_date"],
            "zero_amount_values": sum(record["zero_count"].values()),
            "negative_amount_values": sum(record["negative_count"].values()),
            "unmatched_shipping_orders": joins["orders_without_shipping"] if is_orders else None,
            "unmatched_refund_orders": joins["orders_without_refund"] if is_orders else None,
            "provenance": "external_unverified",
            "finance_verified": "NO",
        })
    return result
