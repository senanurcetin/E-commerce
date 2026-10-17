"""Deterministic positive/negative NEXUS PBIP file acceptance tests."""
from pathlib import Path
import json
import tempfile
import unittest

from scripts.build_powerbi import build, MODEL_NAME, PAGES
from scripts.powerbi_structure_audit import inspect


class PBIPStructureTests(unittest.TestCase):
    def test_generated_seven_page_project_passes_strict_structural_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            build(base, base / "out")
            checked = inspect(base / "out")
            self.assertTrue(checked["static_structure_valid"])
            self.assertEqual(checked["page_count"], 7)
            self.assertEqual(checked["semantic_table_count"], 8)
            self.assertGreater(checked["data_visual_count"], 7)
            self.assertFalse(checked["desktop_render_verified"])
            self.assertFalse(checked["finance_reconciled"])
            self.assertEqual(checked["release_decision"], "HOLD")

    def test_stale_page_and_corrupt_visual_field_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            build(base, base / "out")
            pages = base / "out/project" / (MODEL_NAME + ".Report") / "definition/pages"
            (pages / "legacy_page").mkdir()
            with self.assertRaisesRegex(ValueError, "page directories"):
                inspect(base / "out")
            (pages / "legacy_page").rmdir()

            page = PAGES[1]["id"]
            visual_path = next(v for v in (pages / page / "visuals").glob("*/visual.json")
                               if v.parent.name != "nexus_brand_logo")
            item = json.loads(visual_path.read_text(encoding="utf-8"))
            projection = next(iter(item["visual"]["query"]["queryState"].values()))["projections"][0]
            key = next(iter(projection["field"]))
            projection["field"][key]["Expression"]["SourceRef"]["Entity"] = "OtherMerchant"
            visual_path.write_text(json.dumps(item), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown source"):
                inspect(base / "out")

    def test_tampered_build_evidence_does_not_verify_finance(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            build(base, base / "out")
            path = base / "out/build_evidence.json"
            evidence = json.loads(path.read_text())
            evidence["financial_claims_verified"] = True
            path.write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, "overstates certification"):
                inspect(base / "out")
