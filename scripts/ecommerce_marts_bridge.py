"""Source-isolated E-Commerce/TheLook-style historical dbt marts exporter.

Read-only from the root E-Commerce dbt DuckDB built in target/ci.duckdb.
Raw customer/order identifiers never leave DuckDB. This is NOT owned Lab GA4,
and not Greenweez. A file labelled external remains explicitly unverified.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re

SOURCE = "ecommerce_dbt_marts"
PROVENANCE = ("synthetic_ci", "external_unverified")
DEFAULT_OUTPUT = Path("target/ecommerce_bridge/snapshot.json")
COLUMNS = {
    "orders": ("date", "completed_orders", "returned_orders",
               "completed_revenue", "returned_line_revenue"),
    "sessions": ("date", "sessions", "converted_sessions", "page_view_events"),
}
COUNTS = frozenset(("completed_orders", "returned_orders", "sessions",
                    "converted_sessions", "page_view_events"))

# Deliberately aggregate in DuckDB, never bring raw user or order IDs into
# a JSON export. Actual orders are distinct order_id, not line-item counts.
QUERY = {
    "orders": """
        select cast(order_date as date) as date,
               count(distinct case when lower(order_item_status) = 'complete' then order_id end) as completed_orders,
               count(distinct case when lower(order_item_status) = 'returned' then order_id end) as returned_orders,
               round(sum(revenue), 2) as completed_revenue,
               round(sum(returned_revenue), 2) as returned_line_revenue
        from analytics.fct_order_marketing
        where order_date is not null
        group by 1 order by 1
    """,
    "sessions": """
        select cast(session_date as date) as date,
               count(*) as sessions,
               coalesce(sum(is_converted), 0) as converted_sessions,
               coalesce(sum(page_view_events), 0) as page_view_events
        from analytics.fct_marketing_web_performance
        where session_date is not null
        group by 1 order by 1
    """,
}


def _to_row(key: str, row: dict) -> dict:
    if not isinstance(row, dict) or set(row) != set(COLUMNS[key]):
        raise ValueError(f"{key}: unexpected fields (no raw IDs accepted)")
    try:
        raw_date = row["date"]
        value = raw_date if isinstance(raw_date, date) else date.fromisoformat(raw_date)
    except (ValueError, TypeError) as exc:
        raise ValueError("E-Commerce mart has invalid day grain") from exc
    out = {"date": value.isoformat()}
    for field in COLUMNS[key][1:]:
        n = row[field]
        if isinstance(n, bool) or not isinstance(n, (int, float, Decimal)):
            raise ValueError(f"{key}: invalid numeric field {field}")
        val = float(n)
        if not math.isfinite(val) or val < 0:
            raise ValueError(f"{key}: invalid nonnegative {field}")
        if field in COUNTS:
            if val > 2**53 - 1 or not val.is_integer():
                raise ValueError(f"{key}: non-integer {field}")
            val = int(val)
        out[field] = val
    if key == "sessions" and out["converted_sessions"] > out["sessions"]:
        raise ValueError("Converted sessions cannot exceed sessions")
    return out


def validate_snapshot(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "source_system", "provenance", "generated_at_utc",
        "source_sha256", "tables", "row_counts",
    }:
        raise ValueError("E-Commerce source manifest shape mismatch")
    if value["schema_version"] != 1 or value["source_system"] != SOURCE:
        raise ValueError("E-Commerce source identity/version mismatch")
    if value["provenance"] not in PROVENANCE:
        raise ValueError("Cannot assert verified business provenance")
    if not isinstance(value["source_sha256"], str) or not re.fullmatch("[0-9a-f]{64}", value["source_sha256"]):
        raise ValueError("Invalid source fingerprint")
    try:
        at = datetime.fromisoformat(value["generated_at_utc"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError) as exc:
        raise ValueError("Invalid snapshot timestamp") from exc
    if at.tzinfo is None or at > datetime.now(timezone.utc):
        raise ValueError("Snapshot timestamp invalid or in future")
    tables = value["tables"]
    if not isinstance(tables, dict) or set(tables) != set(COLUMNS):
        raise ValueError("Missing E-Commerce dbt mart")
    normalized = {}
    for key, rows in tables.items():
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Missing E-Commerce {key} observations")
        checked = [_to_row(key, row) for row in rows]
        days = [row["date"] for row in checked]
        if len(days) != len(set(days)):
            raise ValueError(f"Duplicate E-Commerce {key} date")
        normalized[key] = sorted(checked, key=lambda x: x["date"])
    if value.get("row_counts") != {key: len(v) for key, v in normalized.items()}:
        raise ValueError("Source counts do not match E-Commerce mart rows")
    return {**value, "tables": normalized}


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def export_from_duckdb(db: Path, dest: Path = DEFAULT_OUTPUT, *, provenance: str = "synthetic_ci") -> dict:
    if provenance not in PROVENANCE:
        raise ValueError("Unknown E-Commerce provenance; no verified override")
    db = db.resolve(strict=True)
    import duckdb
    con = duckdb.connect(str(db), read_only=True)
    try:
        table_names = {(s, t) for s, t in con.execute(
            "select table_schema, table_name from information_schema.tables"
        ).fetchall()}
        required = {("analytics", "fct_order_marketing"), ("analytics", "fct_marketing_web_performance")}
        if not required <= table_names:
            raise ValueError("Root E-Commerce dbt marts not present in this file")
        result = {}
        for key, sql in QUERY.items():
            cursor = con.execute(sql)
            fields = [col[0] for col in cursor.description]
            result[key] = [dict(zip(fields, row)) for row in cursor.fetchall()]
    finally:
        con.close()
    snapshot = validate_snapshot({
        "schema_version": 1,
        "source_system": SOURCE,
        "provenance": provenance,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": _digest(db),
        "tables": result,
        "row_counts": {k: len(v) for k, v in result.items()},
    })
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(dest)
    return snapshot


def load_snapshot(path: Path = DEFAULT_OUTPUT) -> dict | None:
    if not path.exists():
        return None
    try:
        return validate_snapshot(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"E-Commerce historical snapshot rejected: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--provenance", choices=PROVENANCE, default="synthetic_ci")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    snapshot = export_from_duckdb(args.db, args.output, provenance=args.provenance)
    print("E-Commerce historical mart export completed · "
          f"{snapshot['provenance']} · "
          f"days(orders)={snapshot['row_counts']['orders']}, "
          f"days(sessions)={snapshot['row_counts']['sessions']} · "
          "NOT Lab sales or Greenweez transactions")


if __name__ == "__main__":
    main()
