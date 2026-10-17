"""NEXUS unified workspace status/import tests; no real business data or APIs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import nexus_workspace as workspace


class WorkspaceTests(unittest.TestCase):
    def test_empty_workspace_has_nine_missing_domains_no_false_zero_kpis(self):
        with tempfile.TemporaryDirectory() as folder:
            report = workspace.inspect_sources(Path(folder))
        self.assertEqual(len(report), 9)
        self.assertEqual(set(x["source"] for x in report), set(workspace.SOURCE_LABELS))
        self.assertTrue(all(x["status"] == "missing" for x in report), report)
        self.assertTrue(all(x["rows"] == 0 and not x["real_business_verified"] for x in report))
        self.assertFalse(any("revenue" in item for item in report))

    def test_corrupted_lookalike_rejected_for_all_google_cards(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            p = workspace.paths_for(root)
            p["ecommerce"].parent.mkdir(parents=True, exist_ok=True)
            p["ecommerce"].write_text('{"fake":true}', encoding="utf-8")
            p["google_marts"].mkdir(parents=True, exist_ok=True)
            (p["google_marts"] / "manifest.json").write_text(
                json.dumps({"schema_version": 1, "data_status": "synthetic_demo"}),
                encoding="utf-8",
            )
            report = {x["source"]: x for x in workspace.inspect_sources(root)}
        self.assertEqual(report["ecommerce"]["status"], "invalid")
        self.assertEqual(report["ga4"]["status"], "invalid")
        self.assertEqual(report["gsc"]["status"], "invalid")
        self.assertEqual(report["pagespeed"]["status"], "invalid")
        self.assertEqual(report["greenweez"]["status"], "missing")

    def test_invalid_local_lighthouse_is_not_api_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            folder = workspace.paths_for(root)["local_lighthouse"]
            folder.mkdir(parents=True)
            (folder / "sample.json").write_text('{"score":100}', encoding="utf-8")
            report = {x["source"]: x for x in workspace.inspect_sources(root)}
            self.assertEqual(report["local_lighthouse"]["status"], "invalid")
            self.assertNotEqual(report["local_lighthouse"]["status"], "api_snapshot")

    def test_staged_import_does_not_overwrite_ecommerce_when_greenweez_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            ecommerce = workspace.paths_for(root)["ecommerce"]
            ecommerce.parent.mkdir(parents=True)
            ecommerce.write_text("EXISTING_VERIFIED_FILE_NOT_OVERWRITTEN", encoding="utf-8")

            def good(_db, output, *, provenance):
                self.assertEqual(provenance, "synthetic_ci")
                output.write_text('{"synthetic":true}', encoding="utf-8")

            with patch.object(workspace, "export_ecommerce", side_effect=good) as first, \
                 patch.object(workspace, "export_greenweez", side_effect=ValueError("Bad finance mart")) as second:
                with self.assertRaisesRegex(ValueError, "Bad finance"):
                    workspace._do_import(
                        root, root / "test-a.duckdb", "synthetic_ci",
                        root / "test-b.duckdb", "synthetic_demo",
                    )
            self.assertEqual(ecommerce.read_text(encoding="utf-8"),
                             "EXISTING_VERIFIED_FILE_NOT_OVERWRITTEN")
            first.assert_called_once()
            second.assert_called_once()
            self.assertFalse(workspace.paths_for(root)["greenweez"].exists())

    def test_two_independent_sources_publish_after_both_validations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def export_a(_db, output, *, provenance):
                self.assertEqual(provenance, "synthetic_ci")
                output.write_text("DATA_ECOMMERCE")
            def export_b(_db, output, *, provenance):
                self.assertEqual(provenance, "external_unverified")
                output.write_text("DATA_GREENWEEZ")
            with patch.object(workspace, "export_ecommerce", side_effect=export_a), \
                 patch.object(workspace, "export_greenweez", side_effect=export_b):
                paths = workspace._do_import(
                    root, root / "e.duckdb", "synthetic_ci",
                    root / "g.duckdb", "external_unverified",
                )
            self.assertEqual(len(paths), 2)
            self.assertEqual(workspace.paths_for(root)["ecommerce"].read_text(), "DATA_ECOMMERCE")
            self.assertEqual(workspace.paths_for(root)["greenweez"].read_text(), "DATA_GREENWEEZ")

    def test_import_requires_each_explicit_source_and_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bad_args = (
                (None, None, None, None),
                (root / "e.duckdb", None, None, None),
                (None, "synthetic_ci", None, None),
                (None, None, root / "g.duckdb", None),
                (None, None, None, "synthetic_demo"),
                (root / "e.duckdb", "production_verified", None, None),
                (None, None, root / "g.duckdb", "real_verified"),
            )
            for args in bad_args:
                with self.subTest(args=args), self.assertRaises(ValueError):
                    workspace._do_import(root, *args)
            self.assertFalse((root / "target").exists())


if __name__ == "__main__":
    unittest.main()
