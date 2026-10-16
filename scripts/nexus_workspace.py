"""NEXUS Commerce Intelligence | unified source audit and safe local import.

Use from the E-Commerce repository root:

  python -m scripts.nexus_workspace status
  python -m scripts.nexus_workspace import --ecommerce-db PATH --ecommerce-origin synthetic_ci
  python -m scripts.nexus_workspace import --greenweez-db PATH --greenweez-origin synthetic_demo

The combined import accepts two existing DuckDBs and stages both snapshots
before publication, so a validation error cannot overwrite either previous
file. It does not create DuckDBs, query BigQuery/GA4, or generate demo data.
Business values are NEVER summed across domains.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

from scripts.ecommerce_marts_bridge import (
    export_from_duckdb as export_ecommerce,
    load_snapshot as load_ecommerce,
)
from scripts.greenweez_bridge import (
    export_from_duckdb as export_greenweez,
    load_snapshot as load_greenweez,
)
from scripts.google_dashboard_data import load_bundle
from scripts.lab_ga4_events import load_lab_snapshot
from scripts.local_lighthouse import load_lighthouse_reports
from scripts.greenweez_sheets_observed import load_observed

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_LABELS = {
    "ecommerce": "E-Commerce historical dbt marts",
    "greenweez": "Greenweez finance + paid campaigns",
    "greenweez_sheets": "Greenweez owned source worksheets",
    "commerce_lab_ga4": "NEXUS Commerce Lab opted-in test events",
    "ga4": "Google Analytics acquisition mart",
    "gsc": "Google Search Console search mart",
    "pagespeed": "PageSpeed Insights lab audits",
    "local_lighthouse": "Chrome local Lighthouse laboratory audits",
}
NOT_BUSINESS_EVIDENCE = (
    "Unverified business origin: do not represent as actual trading results "
    "or combine amounts with any other dataset."
)


def paths_for(root: Path) -> dict[str, Path]:
    return {
        "ecommerce": root / "target" / "ecommerce_bridge" / "snapshot.json",
        "greenweez": root / "target" / "greenweez_bridge" / "snapshot.json",
        "greenweez_sheets": root / "target" / "greenweez_bridge" / "google_sheets_observed.json",
        "commerce_lab_ga4": root / "target" / "google_measurement" / "lab_ga4_events.json",
        "google_marts": root / "target" / "google_measurement" / "marts",
        "local_lighthouse": root / "target" / "google_measurement" / "local_lighthouse",
    }


def _record(name: str, status: str, rows: int = 0, provenance: str = "",
            detail: str = "") -> dict:
    if status not in ("missing", "invalid", "synthetic", "external_unverified",
                      "api_snapshot", "api_empty"):
        raise ValueError("Unexpected source availability status")
    return {
        "source": name,
        "label": SOURCE_LABELS[name],
        "status": status,
        "rows": rows,
        "provenance": provenance,
        "detail": detail,
        "real_business_verified": False,
    }


def inspect_sources(root: Path = DEFAULT_ROOT, *, overrides: dict[str, Path] | None = None) -> list[dict]:
    """Never performs network calls, writes or cross-source monetary joins."""
    paths = paths_for(root)
    if overrides:
        if not set(overrides) <= set(paths):
            raise ValueError("Unknown source path override rejected")
        paths.update({k: Path(v) for k, v in overrides.items()})
    report = []

    for name, load in (("ecommerce", load_ecommerce), ("greenweez", load_greenweez)):
        path = paths[name]
        try:
            snapshot = load(path)
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
            report.append(_record(name, "invalid", detail=str(exc)))
            continue
        if snapshot is None:
            report.append(_record(name, "missing", detail="No local validated mart import"))
            continue
        rows = sum(len(t) for t in snapshot["tables"].values())
        prov = snapshot["provenance"]
        report.append(_record(
            name, "synthetic" if prov.startswith("synthetic") else "external_unverified",
            rows, prov, NOT_BUSINESS_EVIDENCE,
        ))

    try:
        observed = load_observed(paths["greenweez_sheets"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        report.append(_record("greenweez_sheets", "invalid", detail=str(exc)))
    else:
        if observed is None:
            report.append(_record("greenweez_sheets", "missing",
                                  detail="Owned worksheets have not been aggregated into a local source report"))
        else:
            rows = sum(observed["row_counts"].values())
            report.append(_record(
                "greenweez_sheets", "external_unverified", rows,
                observed["source_system"],
                "Authenticated worksheet values observed; currency, turnover and cost "
                "semantics not independently audited. No order IDs or campaign names exported.",
            ))

    try:
        lab = load_lab_snapshot(paths["commerce_lab_ga4"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        report.append(_record("commerce_lab_ga4", "invalid", detail=str(exc)))
    else:
        if lab is None:
            report.append(_record("commerce_lab_ga4", "missing",
                                  detail="GA4 web tag may work; independent authorized Data API export not found"))
        else:
            rows, snapshot = lab
            report.append(_record(
                "commerce_lab_ga4", "api_snapshot" if rows else "api_empty",
                len(rows), snapshot["source"],
                "API-observed TEST event counts, never real paid checkout or financial revenue",
            ))

    google_tables = None
    google_status = ""
    google_problem = ""
    try:
        google_tables, _ = load_bundle(paths["google_marts"])
    except FileNotFoundError as exc:
        google_status = "missing" if not (paths["google_marts"] / "manifest.json").exists() else "invalid"
        google_problem = str(exc)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        google_status = "invalid"
        google_problem = str(exc)
    for key in ("ga4", "gsc", "pagespeed"):
        if google_tables is None:
            report.append(_record(key, google_status, detail=google_problem))
        else:
            records = google_tables[key]
            if not records:
                report.append(_record(key, "api_empty", 0,
                                      detail="Valid source manifest exists but no matching rows"))
            else:
                report.append(_record(key, "api_snapshot", len(records),
                                      records[0]["source_system"],
                                      "Validated API snapshot format; not automatically a live feed"))

    try:
        lighthouse = load_lighthouse_reports(paths["local_lighthouse"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        report.append(_record("local_lighthouse", "invalid", detail=str(exc)))
    else:
        report.append(_record(
            "local_lighthouse", "api_snapshot" if lighthouse else "missing",
            len(lighthouse), "local_lighthouse_cli" if lighthouse else "",
            "Local lab run, NOT PSI API nor real-user CrUX metrics" if lighthouse
            else "No verified local Lighthouse JSON files",
        ))

    return report


def _do_import(root: Path, ecommerce_db: Path | None, ecommerce_origin: str | None,
               greenweez_db: Path | None, greenweez_origin: str | None) -> list[str]:
    if ecommerce_db is None and greenweez_db is None:
        raise ValueError("Specify an existing E-Commerce and/or Greenweez DuckDB to import")
    if (ecommerce_db is None) != (ecommerce_origin is None):
        raise ValueError("--ecommerce-db and --ecommerce-origin must be supplied together")
    if (greenweez_db is None) != (greenweez_origin is None):
        raise ValueError("--greenweez-db and --greenweez-origin must be supplied together")
    if ecommerce_origin is not None and ecommerce_origin not in ("synthetic_ci", "external_unverified"):
        raise ValueError("E-Commerce origin is not an accepted evidence category")
    if greenweez_origin is not None and greenweez_origin not in ("synthetic_demo", "external_unverified"):
        raise ValueError("Greenweez origin is not an accepted evidence category")

    # Validate ALL requested sources before touching any published snapshot.
    root_target = root / "target"
    root_target.mkdir(parents=True, exist_ok=True)
    publishes = []
    with tempfile.TemporaryDirectory(prefix=".nexus-source-staging-", dir=root_target) as folder:
        tmp = Path(folder)
        if ecommerce_db is not None:
            candidate = tmp / "ecommerce.json"
            export_ecommerce(ecommerce_db, candidate, provenance=ecommerce_origin)
            publishes.append((candidate, paths_for(root)["ecommerce"]))
        if greenweez_db is not None:
            candidate = tmp / "greenweez.json"
            export_greenweez(greenweez_db, candidate, provenance=greenweez_origin)
            publishes.append((candidate, paths_for(root)["greenweez"]))
        for stage, dest in publishes:
            # Both have been fully validated at this point, before publishing.
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage, dest)
    return [str(dest) for _, dest in publishes]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="Absolute checkout path (defaults to script's own E-Commerce checkout)")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="Report per-source status without fetching or exporting")
    status.add_argument("--json", action="store_true", help="Machine-readable source status")
    stage = commands.add_parser("import", help="Import existing DuckDB marts with explicit provenance")
    stage.add_argument("--ecommerce-db", type=Path)
    stage.add_argument("--ecommerce-origin", choices=("synthetic_ci", "external_unverified"))
    stage.add_argument("--greenweez-db", type=Path)
    stage.add_argument("--greenweez-origin", choices=("synthetic_demo", "external_unverified"))
    args = parser.parse_args()
    if args.command == "status":
        items = inspect_sources(args.root)
        if args.json:
            print(json.dumps({"schema_version": 1,
                              "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                              "sources": items}, indent=2))
        else:
            for item in items:
                print(f"{item['source']:<21} {item['status']:<20} rows={item['rows']:<5} "
                      f"{item['provenance']}")
                if item["status"] in ("missing", "invalid"):
                    print("  reason: " + item["detail"])
            print("No totals are ever added across independent data sources.")
        return 0
    published = _do_import(args.root, args.ecommerce_db, args.ecommerce_origin,
                           args.greenweez_db, args.greenweez_origin)
    for path in published:
        print(f"Validated local source snapshot published: {path}")
    print("Provenance is preserved; neither source is automatically business-verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
