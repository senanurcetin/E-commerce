"""Resolve exact BigQuery source-location candidates from metadata inventory only.

No BigQuery API calls, SQL, credential access or dbt writes. Output is *advisory*:
a human must inspect evidence and explicitly set dbt --vars.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.cloud_source_inventory import EXPECTED, PROJECTS, OUT as INVENTORY_PATH

OUTPUT = Path("target/cloud_inventory/source_mapping_candidates.json")
VAR_NAMES = {
    "ecommerce": ("ecommerce_source_project", "ecommerce_source_dataset"),
    "greenweez_raw": ("greenweez_raw_project", "greenweez_raw_dataset"),
    "greenweez_gsheet": ("greenweez_gsheet_project", "greenweez_gsheet_dataset"),
}


def resolve(inventory: dict) -> dict:
    if not isinstance(inventory, dict) or inventory.get("schema_version") != 1:
        raise ValueError("Unsupported inventory schema; run cloud_source_inventory first")
    projects = inventory.get("results")
    if not isinstance(projects, list) or len(projects) != len(PROJECTS):
        raise ValueError("Expected precisely the two authorized project results")
    by_project = {}
    for project in projects:
        if not isinstance(project, dict) or project.get("project") not in PROJECTS:
            raise ValueError("Unexpected project in metadata inventory")
        name = project["project"]
        if name in by_project:
            raise ValueError("Duplicate project in metadata inventory")
        by_project[name] = project

    # An inaccessible dataset could contain another full candidate; never claim
    # unique discovery in a partially visible inventory.
    complete = all(
        p["status"] == "listed" and not p.get("metadata_errors")
        and isinstance(p.get("datasets"), list)
        and all(isinstance(d, dict) and d.get("status") == "listed"
                for d in p["datasets"])
        for p in by_project.values()
    )
    decisions = {}
    for domain, required in EXPECTED.items():
        candidates = []
        for project_name in PROJECTS:
            for entry in by_project[project_name].get("datasets", []):
                if not isinstance(entry, dict):
                    continue
                dataset = entry.get("dataset")
                if not isinstance(dataset, str) or not dataset:
                    continue
                match = entry.get("matches", {}).get(domain, {})
                found = match.get("found", []) if isinstance(match, dict) else []
                if isinstance(found, list) and set(found) == set(required) and len(found) == len(required):
                    candidates.append({"project": project_name, "dataset": dataset})
        if not complete:
            status = "inventory_incomplete"
        elif not candidates:
            status = "no_complete_match"
        elif len(candidates) != 1:
            status = "ambiguous"
        else:
            status = "ready_for_manual_review"
        item = {"status": status, "required_tables": list(required),
                "complete_candidates": candidates}
        if status == "ready_for_manual_review":
            pvar, dvar = VAR_NAMES[domain]
            item["suggested_dbt_vars"] = {
                pvar: candidates[0]["project"], dvar: candidates[0]["dataset"],
            }
        decisions[domain] = item
    return {
        "schema_version": 1,
        "inventory_scanned_at_utc": inventory.get("scanned_at_utc"),
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(),
        "inventory_complete": complete,
        "status": "all_unique" if all(d["status"] == "ready_for_manual_review"
                                      for d in decisions.values()) else "needs_review",
        "sources": decisions,
        "warning": "Advisory metadata only; not proof of row quality, freshness or permissions to query.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    try:
        report = resolve(json.loads(args.inventory.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as exc:
        print("BLOCKED: metadata inventory invalid or missing: " + str(exc))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for domain, decision in report["sources"].items():
        print(domain + ": " + decision["status"] +
              "; complete candidates=" + str(len(decision["complete_candidates"])))
    print("Evidence-only mapping report:", args.output)
    return 0 if report["status"] == "all_unique" else 1


if __name__ == "__main__":
    raise SystemExit(main())
