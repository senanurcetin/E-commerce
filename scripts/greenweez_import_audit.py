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


# Exact table/column allowlists from the source-projected Greenweez DuckDB.
# No IDs or original money totals are materialized in application responses.
SOURCE_CONTRACTS = {
    "gwz_finance_orders_orders": (
        "orders_id", "datetime", ("turnover", "purchase_cost", "ship_fee")
    ),
    "gwz_finance_shipping_shipping": (
        "orders_id", "date_date", ("log_cost", "ship_cost")
    ),
    "gwz_finance_refund_sheet_1": (
        "orders_id", "datetime", ("refund",)
    ),
    "gwz_finance_campaign": (None, "datetime", ("cost",)),
}


def verify_physical_tables(connection, audit: dict) -> None:
    """Reconcile embedded audit against real DuckDB tables using SQL aggregates.

    This catches missing/replaced tables, modified dates/counts, changed zero or
    negative amounts, key duplicates and broken order-side link coverage.
    It is a structural consistency check, NOT cryptographic integrity and NOT
    independent certification of a merchant's business accounting.
    """
    audit = validate_audit(audit)
    for table, (key, date_field, amounts) in SOURCE_CONTRACTS.items():
        physical = {
            row[0] for row in connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='analytics' AND table_name=?",
                [table],
            ).fetchall()
        }
        required = ({key} if key else set()) | {date_field} | set(amounts)
        if physical != required:
            raise ValueError(f"{table}: missing, extra or replaced source columns")

        day = f"TRY_CAST(SUBSTR(CAST({date_field} AS VARCHAR), 1, 10) AS DATE)"
        expressions = [
            "COUNT(*) AS row_count",
            f"MIN({day}) AS min_date",
            f"MAX({day}) AS max_date",
            f"SUM(CASE WHEN {day} IS NULL THEN 1 ELSE 0 END) AS invalid_dates",
        ]
        if key:
            expressions.extend([
                f"SUM(CASE WHEN TRY_CAST({key} AS BIGINT) IS NULL "
                "THEN 1 ELSE 0 END) AS invalid_keys",
                f"COUNT(DISTINCT TRY_CAST({key} AS BIGINT)) AS distinct_keys",
            ])
        for field in amounts:
            as_number = f"TRY_CAST({field} AS DOUBLE)"
            expressions.extend([
                f"SUM(CASE WHEN {as_number} IS NULL "
                f"THEN 1 ELSE 0 END) AS invalid_{field}",
                f"SUM(CASE WHEN {as_number} < 0 "
                f"THEN 1 ELSE 0 END) AS negative_{field}",
                f"SUM(CASE WHEN {as_number} = 0 "
                f"THEN 1 ELSE 0 END) AS zero_{field}",
            ])
        values = connection.execute(
            "SELECT " + ", ".join(expressions) + f" FROM analytics.{table}"
        ).fetchone()
        row_count, start, end, invalid_dates = values[:4]
        expected = audit["tables"][table]
        if (row_count != expected["rows"] or invalid_dates != 0
                or start is None or end is None
                or start.isoformat() != expected["start_date"]
                or end.isoformat() != expected["end_date"]):
            raise ValueError(f"{table}: source row count or date coverage differs from audit")
        index = 4
        if key:
            invalid_keys, unique_keys = values[index:index + 2]
            index += 2
            if invalid_keys or unique_keys != row_count:
                raise ValueError(f"{table}: source order key integrity differs from audit")
        for field in amounts:
            invalid, negative, zero = values[index:index + 3]
            index += 3
            if (invalid or
                    negative != expected["negative_count"][field] or
                    zero != expected["zero_count"][field]):
                raise ValueError(f"{table}: source amount distribution differs from audit")
        if not key and row_count != connection.execute(
            f"SELECT COUNT(DISTINCT {day}) FROM analytics.{table}"
        ).fetchone()[0]:
            raise ValueError(f"{table}: duplicated campaign source day")

    for label, source in (
        ("shipping", "gwz_finance_shipping_shipping"),
        ("refund", "gwz_finance_refund_sheet_1"),
    ):
        missing = connection.execute(
            "SELECT COUNT(*) FROM analytics.gwz_finance_orders_orders AS orders "
            f"LEFT JOIN analytics.{source} AS linked "
            "ON TRY_CAST(orders.orders_id AS BIGINT) = "
            "TRY_CAST(linked.orders_id AS BIGINT) "
            "WHERE linked.orders_id IS NULL"
        ).fetchone()[0]
        if missing != audit["join_coverage"][f"orders_without_{label}"]:
            raise ValueError(f"Greenweez {label} join coverage differs from source audit")



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
            if len(rows) != 1 or not isinstance(rows[0][0], str):
                raise ValueError("Greenweez import evidence must have exactly one JSON report")
            try:
                record = json.loads(rows[0][0])
            except json.JSONDecodeError as exc:
                raise ValueError("Greenweez import evidence JSON invalid") from exc
            validate_audit(record)
            verify_physical_tables(connection, record)
            return record
        finally:
            connection.close()
    except duckdb.Error as exc:
        # Avoid disclosing raw SQL errors or private source content through UI.
        raise ValueError("Greenweez local tables do not match import quality evidence") from exc


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
