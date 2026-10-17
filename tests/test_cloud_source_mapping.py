"""Fail-closed offline mapping tests: no GCP credentials or network needed."""
import unittest
from pathlib import Path

from scripts import cloud_source_inventory as inv
from scripts import cloud_source_mapping as mapping


def fake_inventory(duplicated=False, partial=False, missing=False):
    rows = []
    for i, project in enumerate(inv.PROJECTS):
        datasets = []
        if i == 0 or duplicated:
            for domain, required in inv.EXPECTED.items():
                if missing and domain == "greenweez_raw":
                    continue
                datasets.append({
                    "dataset": domain + "_dataset",
                    "status": "listed",
                    "matches": {domain: {"found": list(required)}},
                })
        rows.append({
            "project": project, "status": "listed",
            "metadata_errors": [{"reason": "HTTP 403"}] if partial and i == 1 else [],
            "datasets": datasets,
        })
    return {"schema_version": 1, "results": rows}


class SourceMappingTests(unittest.TestCase):
    def test_unique_complete_three_domains(self):
        report = mapping.resolve(fake_inventory())
        self.assertTrue(report["inventory_complete"])
        self.assertEqual(report["status"], "all_unique")
        self.assertEqual(report["sources"]["ecommerce"]["suggested_dbt_vars"],
                         {"ecommerce_source_project": "workintech-working",
                          "ecommerce_source_dataset": "ecommerce_dataset"})

    def test_partial_permissions_never_claim_unique_source(self):
        report = mapping.resolve(fake_inventory(partial=True))
        self.assertFalse(report["inventory_complete"])
        self.assertEqual(report["sources"]["ecommerce"]["status"], "inventory_incomplete")
        self.assertNotIn("suggested_dbt_vars", report["sources"]["ecommerce"])

    def test_duplicate_full_matches_require_manual_resolution(self):
        report = mapping.resolve(fake_inventory(duplicated=True))
        self.assertEqual(report["sources"]["greenweez_raw"]["status"], "ambiguous")
        self.assertNotIn("suggested_dbt_vars", report["sources"]["greenweez_raw"])

    def test_missing_required_tables_not_assumed_present(self):
        report = mapping.resolve(fake_inventory(missing=True))
        self.assertEqual(report["sources"]["greenweez_raw"]["status"], "no_complete_match")

    def test_unknown_or_duplicate_projects_rejected(self):
        report = fake_inventory()
        report["results"][1]["project"] = "unauthorized"
        with self.assertRaises(ValueError):
            mapping.resolve(report)
        report["results"][1]["project"] = inv.PROJECTS[0]
        with self.assertRaises(ValueError):
            mapping.resolve(report)

    def test_source_yaml_has_explicit_default_and_override(self):
        root = Path(__file__).resolve().parents[1]
        expected = {
            "models/staging/source.yml": ["ecommerce_source_project", "ecommerce_source_dataset"],
            "integrations/greenweez/models/staging/schema.yml": ["greenweez_raw_project", "greenweez_raw_dataset"],
            "integrations/greenweez/models/staging/gsheet/schema.yml": ["greenweez_gsheet_project", "greenweez_gsheet_dataset"],
        }
        for path, keys in expected.items():
            source = (root / path).read_text(encoding="utf-8")
            for key in keys:
                self.assertIn("var('" + key + "'", source)


if __name__ == "__main__":
    unittest.main()



class KnownDatasetEvidenceTests(unittest.TestCase):
    def test_known_full_source_pin_visible_even_if_global_scan_incomplete(self):
        inventory = fake_inventory(partial=True)
        # Correctly named existing source dataset; other project remains inaccessible.
        sheets = next(d for d in inventory["results"][0]["datasets"]
                      if "greenweez_gsheet" in d["matches"])
        sheets["dataset"] = "fvt_gsheet"
        report = mapping.resolve(inventory)
        item = report["sources"]["greenweez_gsheet"]
        self.assertEqual(item["status"], "inventory_incomplete")
        self.assertNotIn("suggested_dbt_vars", item)
        self.assertEqual(item["pinned_source_table_contract"]["dataset"], "fvt_gsheet")
        self.assertEqual(report["status"], "needs_review")

    def test_no_false_pin_for_other_ambiguous_source(self):
        inventory = fake_inventory(duplicated=True)
        report = mapping.resolve(inventory)
        self.assertNotIn("pinned_source_table_contract",
                         report["sources"]["greenweez_raw"])
