"""Verify both synthetic dbt marts -> NEXUS -> seven-page PBIP in one CI job.

No BigQuery, Vercel, GA4, credentials, or claims about real finance.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.build_powerbi import build
from scripts.ecommerce_marts_bridge import load_snapshot as load_ecommerce
from scripts.greenweez_bridge import load_snapshot as load_greenweez
from scripts.nexus_workspace import inspect_sources, paths_for
from scripts.powerbi_structure_audit import inspect


def verify(root: Path, out: Path) -> dict:
    root = Path(root)
    paths = paths_for(root)
    ecommerce = load_ecommerce(paths["ecommerce"])
    greenweez = load_greenweez(paths["greenweez"])
    if ecommerce is None or greenweez is None:
        raise ValueError("Both independently built synthetic snapshots required")
    if (ecommerce["provenance"] != "synthetic_ci"
            or greenweez["provenance"] != "synthetic_demo"):
        raise ValueError("Offline CI accepts only explicit synthetic provenance")
    if (not ecommerce["tables"]["orders"] or not ecommerce["tables"]["sessions"]
            or not greenweez["tables"]["daily"]):
        raise ValueError("dbt mart outputs must be nonempty")
    statuses = {row["source"]: row for row in inspect_sources(root)}
    for key in ("ecommerce", "greenweez"):
        if statuses[key]["status"] != "synthetic":
            raise ValueError("NEXUS source status does not match source provenance")
    if any(row["real_business_verified"] for row in statuses.values()):
        raise ValueError("Offline workflow cannot self-certify real business metrics")
    evidence = build(root, out)
    structure = inspect(out)
    counts = evidence["exported_table_rows"]
    expected = {
        "ECommerceOrders": len(ecommerce["tables"]["orders"]),
        "ECommerceSessions": len(ecommerce["tables"]["sessions"]),
        "GreenweezFinance": len(greenweez["tables"]["daily"]),
        "SourceRegistry": len(statuses),
    }
    for table, count in expected.items():
        if counts.get(table) != count:
            raise ValueError(f"{table}: source count differs from PBIP export")
        with (out / "marts" / (table + ".csv")).open(
                encoding="utf-8-sig", newline="") as stream:
            if sum(1 for _ in csv.DictReader(stream)) != count:
                raise ValueError(f"{table}: CSV contains unexpected row count")
    with (out / "marts/SourceRegistry.csv").open(
            encoding="utf-8-sig", newline="") as stream:
        registered = {row["source"]: row for row in csv.DictReader(stream)}
    for source in ("E-Commerce historical dbt marts",
                   "Greenweez finance + paid campaigns"):
        if registered.get(source, {}).get("status") != "synthetic":
            raise ValueError("Power BI registry lost synthetic source provenance")
    if (not structure["static_structure_valid"]
            or structure["desktop_render_verified"]
            or structure["finance_reconciled"]
            or evidence["financial_claims_verified"]
            or evidence["powerbi_desktop_accepted"]):
        raise ValueError("No finance or Desktop acceptance in CI")
    return {
        "schema_version": 1,
        "offline_integration_passed": True,
        "root_dbt_days": expected["ECommerceOrders"] + expected["ECommerceSessions"],
        "greenweez_dbt_daily_rows": expected["GreenweezFinance"],
        "source_groups": len(statuses),
        "pbip_pages": structure["page_count"],
        "provenance": "synthetic_ci_only",
        "bigquery_live_verified": False,
        "powerbi_desktop_accepted": False,
        "financial_claims_verified": False,
        "release_decision": "HOLD",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("target/powerbi"))
    args = parser.parse_args(argv)
    try:
        result = verify(args.root, args.out)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print("BLOCKED: offline integration verification failed:", str(exc))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
