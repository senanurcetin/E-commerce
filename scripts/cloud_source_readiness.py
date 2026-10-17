"""Metadata-only P0 source readiness report; does NOT touch Google APIs or rows.

Inputs: the owner's locally generated BigQuery inventory and resolver JSONs.
The report includes only approved domain-specific table names and selected
project/dataset IDs, never unrelated dataset names or table contents.

Ready-for-DRY-RUN is NOT ready-for-production: schemas, query permissions,
billing bytes, row quality, currency and refunds require additional gates.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.cloud_source_inventory import EXPECTED, PROJECTS
from scripts.cloud_source_mapping import resolve

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "target/cloud_inventory/bq_source_locations.json"
MAPPING = ROOT / "target/cloud_inventory/source_mapping_candidates.json"
OUTPUT = ROOT / "target/cloud_inventory/p0_readiness.json"
PINNED = {
    "ecommerce": ("workintech-working", "e_ticaret"),
    "greenweez_gsheet": ("workintech-working", "fvt_gsheet"),
}
RAW_PARTIAL = ("data-analiz-490513", "gz_raw_data")
ALTERNATIVE = ("data-analiz-490513", "thelook_ecommerce")


def _listed(inventory: dict) -> dict[tuple[str, str], dict]:
    results = inventory.get("results")
    if not isinstance(results, list) or len(results) != len(PROJECTS):
        raise ValueError("Unexpected BigQuery project scope")
    names, entries = set(), {}
    for project in results:
        if not isinstance(project, dict) or project.get("project") not in PROJECTS:
            raise ValueError("Unknown BigQuery project")
        name = project["project"]
        if name in names:
            raise ValueError("Duplicate BigQuery project")
        names.add(name)
        if project.get("status") != "listed" or not isinstance(project.get("datasets"), list):
            raise ValueError("Project-level metadata unavailable")
        for dataset in project["datasets"]:
            if not isinstance(dataset, dict) or not isinstance(dataset.get("dataset"), str):
                raise ValueError("Invalid dataset metadata")
            identity = (name, dataset["dataset"])
            if identity in entries:
                raise ValueError("Duplicate dataset metadata")
            entries[identity] = dataset
    return entries


def _coverage(entries: dict, identity: tuple[str, str], domain: str) -> dict:
    required = set(EXPECTED[domain])
    target = entries.get(identity)
    if target is None or target.get("status") != "listed":
        return {"tables_found": 0, "tables_required": len(required), "table_names_confirmed": False}
    matches = target.get("matches", {})
    match = matches.get(domain) if isinstance(matches, dict) else None
    found = match.get("found", []) if isinstance(match, dict) else []
    if not isinstance(found, list) or len(found) != len(set(found)):
        raise ValueError("Invalid or duplicate expected source table identifiers")
    present = set(found)
    if not present <= required:
        raise ValueError("Unexpected source table match")
    # Metadata-only resolver stores exact required table-name matches.
    return {
        "tables_found": len(present), "tables_required": len(required),
        "table_names_confirmed": present == required,
    }


def evaluate(inventory: dict, mapping: dict) -> dict:
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise ValueError("Unsupported BigQuery inventory")
    if not isinstance(mapping, dict) or mapping.get("schema_version") != 1:
        raise ValueError("Unsupported source mapping")
    if (not inventory.get("scanned_at_utc")
            or mapping.get("inventory_scanned_at_utc") != inventory.get("scanned_at_utc")):
        raise ValueError("Source mapping and inventory scans do not match")
    entries = _listed(inventory)
    # Independent recomputation excludes hand-edited/fabricated candidate sets.
    expected_mapping = resolve(inventory)
    reported_sources = mapping.get("sources")
    if not isinstance(reported_sources, dict) or set(reported_sources) != set(EXPECTED):
        raise ValueError("Expected three source domains")
    for domain in EXPECTED:
        reported = reported_sources[domain]
        expected = expected_mapping["sources"][domain]
        if (not isinstance(reported, dict)
                or reported.get("status") != expected["status"]
                or reported.get("required_tables") != expected["required_tables"]
                or reported.get("complete_candidates") != expected["complete_candidates"]):
            raise ValueError("Source mapping differs from recomputed inventory evidence")
    ecom = _coverage(entries, PINNED["ecommerce"], "ecommerce")
    sheets = _coverage(entries, PINNED["greenweez_gsheet"], "greenweez_gsheet")
    alt = _coverage(entries, ALTERNATIVE, "ecommerce")
    raw = _coverage(entries, RAW_PARTIAL, "greenweez_raw")
    return {
        "schema_version": 1,
        "evidence_scanned_at_utc": inventory["scanned_at_utc"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "global_inventory_complete": expected_mapping["inventory_complete"],
        "data_rows_queried": False,
        "bigquery_schema_checked": False,
        "bigquery_cost_checked": False,
        "financial_semantics_verified": False,
        "p0_live_preflight_complete": False,
        "sources": {
            "ecommerce": {
                "project": PINNED["ecommerce"][0],
                "dataset": PINNED["ecommerce"][1],
                **ecom,
                "status": "ready_for_independent_live_preflight" if ecom["table_names_confirmed"] else "blocked",
            },
            "ecommerce_alternative": {
                "project": ALTERNATIVE[0], "dataset": ALTERNATIVE[1],
                **alt, "status": "separate_candidate_do_not_union",
            },
            "greenweez_gsheet": {
                "project": PINNED["greenweez_gsheet"][0],
                "dataset": PINNED["greenweez_gsheet"][1],
                **sheets,
                "status": "ready_for_independent_live_preflight" if sheets["table_names_confirmed"] else "blocked",
            },
            "greenweez_raw": {
                "project": RAW_PARTIAL[0], "dataset": RAW_PARTIAL[1],
                **raw,
                "status": "blocked_incomplete_marketing_source_tables",
            },
        },
        "next_gate": ("Authorized BigQuery live schema and dry-run cost/permission "
                      "check of all four Greenweez Sheets tables; NO execution implied."),
        "warning": "Metadata table-name readiness only. No row, billing or business KPI certification.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = evaluate(
            json.loads(args.inventory.read_text(encoding="utf-8")),
            json.loads(args.mapping.read_text(encoding="utf-8")),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("BLOCKED: local P0 source evidence invalid: " + str(exc))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    for name, value in report["sources"].items():
        print(f"{name}: {value['tables_found']}/{value['tables_required']} table names; {value['status']}")
    print("LIVE PREFLIGHT: HOLD; no data rows or BigQuery queries run.")
    print("Aggregate metadata report written:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
