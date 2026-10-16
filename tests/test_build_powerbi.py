"""NEXUS Power BI reproducibility and source-governance integration tests."""
import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_powerbi import build, TABLES, PAGES, MODEL_NAME, MEASURES


class PBIPBuildTests(unittest.TestCase):
    def test_empty_sources_never_invent_business_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            out = root / "target" / "powerbi"
            result = build(root, out)
            self.assertEqual(result["exported_table_rows"]["ECommerceOrders"], 0)
            self.assertEqual(result["exported_table_rows"]["GreenweezFinance"], 0)
            self.assertEqual(result["exported_table_rows"]["CommerceLabEvents"], 0)
            self.assertEqual(len(result["pages"]), 6)
            self.assertFalse(result["powerbi_desktop_accepted"])
            self.assertFalse(result["financial_claims_verified"])
            for name, fields in TABLES.items():
                with (out / "marts" / f"{name}.csv").open(
                    encoding="utf-8-sig", newline="",
                ) as handle:
                    r = list(csv.DictReader(handle))
                    if name == "SourceRegistry":
                        self.assertEqual(len(r), 8)
                    else:
                        self.assertEqual(r, [], f"{name}: fabricated source KPI")
            project = out / "project"
            p = json.loads((project / f"{MODEL_NAME}.pbip").read_text())
            self.assertEqual(p["artifacts"][0]["report"]["path"], f"{MODEL_NAME}.Report")
            pbir = json.loads(
                (project / f"{MODEL_NAME}.Report" / "definition.pbir").read_text()
            )
            self.assertEqual(pbir["datasetReference"]["byPath"]["path"],
                             f"../{MODEL_NAME}.SemanticModel")
            pages = json.loads(
                (project / f"{MODEL_NAME}.Report" /
                 "definition/pages/pages.json").read_text()
            )
            self.assertEqual(pages["pageOrder"], [p["id"] for p in PAGES])
            for page in PAGES:
                page_dir = (project / f"{MODEL_NAME}.Report" /
                            "definition/pages" / page["id"])
                self.assertEqual(json.loads(
                    (page_dir / "page.json").read_text())["displayName"],
                    page["title"])
                self.assertEqual(len(list(page_dir.glob("visuals/*/visual.json"))),
                                 len(page["cards"]) + len(page["charts"]))
            tmdl_dir = project / f"{MODEL_NAME}.SemanticModel" / "definition/tables"
            self.assertEqual(len(list(tmdl_dir.glob("*.tmdl"))), len(TABLES))
            text = (tmdl_dir / "GreenweezOrdersObserved.tmdl").read_text()
            self.assertIn("Rows Missing Turnover", text)
            self.assertNotIn("RETURN 0", text)

    def test_project_generation_is_idempotent_and_no_joined_revenue(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = build(root, root / "out")
            second = build(root, root / "out")
            self.assertEqual(first["pages"], second["pages"])
            combined = " ".join(
                f"{expr} {fmt}" for measures in MEASURES.values()
                for expr, fmt in measures.values()
            )
            self.assertNotIn("LOOKUPVALUE", combined)
            self.assertNotIn("RELATED(", combined)
            self.assertNotIn("UNION(", combined)
            self.assertNotIn("GA4 revenue", combined)

    def test_source_observation_csv_explicitly_excludes_order_identifiers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            build(root, root / "out")
            for name in TABLES:
                fields = [v for v, _ in TABLES[name]]
                for forbidden in ("orders_id", "campaign_key", "customer_email",
                                  "user_id", "ga_client_id"):
                    self.assertNotIn(forbidden, fields)


if __name__ == "__main__":
    unittest.main()
