"""Verify NEXUS-generated PBIP source integrity without Power BI Desktop.

A PASS here means strictly that on-disk PBIP, semantic model and CSV artifacts
agree with the documented 7-page NEXUS generator. It is NOT a Desktop render,
model refresh, enterprise policy review or financial reconciliation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from scripts.build_powerbi import (
    BRAND_LOGO_NAME, BRAND_THEME_NAME, MEASURES, MODEL_NAME, PAGES, TABLES,
)


def _json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Power BI artifact must contain a JSON object")
    return result


def inspect(out: Path) -> dict:
    """Fail closed on stale pages, broken visual bindings or unsupported joins."""
    out = Path(out)
    project = out / "project"
    report_dir = project / (MODEL_NAME + ".Report")
    model_dir = project / (MODEL_NAME + ".SemanticModel")
    definition = report_dir / "definition"
    actual_pages = definition / "pages"
    page_list = _json(actual_pages / "pages.json")
    expected_ids = [page["id"] for page in PAGES]
    if len(expected_ids) != len(set(expected_ids)) or len(PAGES) != 7:
        raise ValueError("Generator page identity is inconsistent")
    if (page_list.get("pageOrder") != expected_ids
            or page_list.get("activePageName") != expected_ids[0]):
        raise ValueError("Seven-page order or active page differs from NEXUS contract")
    if {p.name for p in actual_pages.iterdir() if p.is_dir()} != set(expected_ids):
        raise ValueError("Old/unknown/missing Power BI page directories found")
    if set(p.name for p in (model_dir / "definition" / "tables").glob("*.tmdl")) != {
            name + ".tmdl" for name in TABLES}:
        raise ValueError("Missing or unexpected semantic tables")
    if list((model_dir / "definition").rglob("*relationships*.tmdl")):
        raise ValueError("Undocumented cross-source relationship definition")

    report = _json(definition / "report.json")
    if report.get("themeCollection", {}).get("customTheme", {}).get("name") != BRAND_THEME_NAME:
        raise ValueError("NEXUS custom theme registration missing")
    resources = report.get("resourcePackages", [])
    if len(resources) != 1 or {x.get("name") for x in resources[0].get("items", [])} != {
            BRAND_LOGO_NAME, BRAND_THEME_NAME}:
        raise ValueError("NEXUS static resource manifest mismatch")
    resource_dir = report_dir / "StaticResources" / "RegisteredResources"
    if (not (resource_dir / BRAND_LOGO_NAME).is_file()
            or not (resource_dir / BRAND_THEME_NAME).is_file()):
        raise ValueError("NEXUS theme or logo asset missing")
    if not (resource_dir / BRAND_LOGO_NAME).read_bytes():
        raise ValueError("NEXUS image asset empty")

    for name, fields in TABLES.items():
        with (out / "marts" / (name + ".csv")).open(
                encoding="utf-8-sig", newline="") as handle:
            csv_rows = csv.reader(handle)
            if next(csv_rows, None) != [field for field, _ in fields]:
                raise ValueError(f"{name}: missing or reordered CSV header")
            # source rows intentionally not materialized by this audit.
        tmdl = (model_dir / "definition" / "tables" / (name + ".tmdl")).read_text(
            encoding="utf-8")
        if not tmdl.startswith("table " + name + "\n"):
            raise ValueError(f"{name}: incorrect TMDL table identity")
        for field, _ in fields:
            if "\tcolumn " + field + "\n" not in tmdl:
                raise ValueError(f"{name}: missing TMDL field")
        for measure in MEASURES.get(name, {}):
            if "\tmeasure '" + measure + "' = " not in tmdl:
                raise ValueError(f"{name}: required scoped measure unavailable")

    visual_count = 0
    for page in PAGES:
        pdir = actual_pages / page["id"]
        definition_page = _json(pdir / "page.json")
        if (definition_page.get("name") != page["id"]
                or definition_page.get("displayName") != page["title"]):
            raise ValueError("Page ID/title does not match generator contract")
        expected_count = 1 + len(page["cards"]) + len(page["charts"])
        visuals = list((pdir / "visuals").glob("*/visual.json"))
        if len(visuals) != expected_count:
            raise ValueError("Page visual count differs from generator")
        if {p.parent.name for p in visuals} != {
                "nexus_brand_logo", *[f"{n:020x}" for n in range(1, expected_count)]}:
            raise ValueError("Stale or unexpected generated visual ID")
        logo = _json(pdir / "visuals" / "nexus_brand_logo" / "visual.json")
        if (logo.get("visual", {}).get("visualType") != "image"
                or logo["visual"]["objects"]["image"][0]["properties"]["sourceFile"]
                ["image"]["url"]["expr"]["ResourcePackageItem"]["ItemName"] != BRAND_LOGO_NAME):
            raise ValueError("Missing official logo visual reference")
        for vpath in visuals:
            if vpath.parent.name == "nexus_brand_logo":
                continue
            visual = _json(vpath)["visual"]
            roles = visual.get("query", {}).get("queryState", {})
            for role in roles.values():
                for projection in role.get("projections", []):
                    field = projection.get("field", {})
                    if not isinstance(field, dict) or len(field) != 1:
                        raise ValueError("Unknown visual field binding")
                    kind, spec = next(iter(field.items()))
                    if kind not in ("Measure", "Column"):
                        raise ValueError("Non-source-scoped visual projection")
                    table = spec["Expression"]["SourceRef"]["Entity"]
                    member = spec["Property"]
                    if table not in TABLES:
                        raise ValueError("Visual references unknown source dataset")
                    expected = (set(MEASURES.get(table, {})) if kind == "Measure"
                                else {col for col, _ in TABLES[table]})
                    if member not in expected:
                        raise ValueError("Visual references missing scoped measure/column")
                    if projection.get("queryRef") != table + "." + member:
                        raise ValueError("Visual binding table and property mismatch")
            visual_count += 1

    evidence = _json(out / "build_evidence.json")
    if (evidence.get("pages") != [p["title"] for p in PAGES]
            or set(evidence.get("exported_table_rows", {})) != set(TABLES)
            or evidence.get("powerbi_desktop_accepted") is not False
            or evidence.get("financial_claims_verified") is not False):
        raise ValueError("Power BI build evidence is missing or overstates certification")
    return {
        "schema_version": 1,
        "static_structure_valid": True,
        "page_count": len(PAGES),
        "semantic_table_count": len(TABLES),
        "data_visual_count": visual_count,
        "desktop_render_verified": False,
        "finance_reconciled": False,
        "release_decision": "HOLD",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("target/powerbi"))
    args = parser.parse_args(argv)
    try:
        report = inspect(args.out)
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print("BLOCKED: PBIP structural verification failed:", str(exc))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
