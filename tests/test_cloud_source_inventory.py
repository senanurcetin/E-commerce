"""Offline contract tests: no external BigQuery credentials, data rows or SQL."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import cloud_source_inventory as inv


class CloudInventoryTests(unittest.TestCase):
    def test_defaults_include_exactly_two_user_projects(self):
        self.assertEqual(inv.PROJECTS,
                         ("workintech-working", "data-analiz-490513"))
        self.assertEqual(set(inv.EXPECTED), {"ecommerce", "greenweez_raw",
                                             "greenweez_gsheet"})

    @patch("scripts.cloud_source_inventory.subprocess.run")
    def test_auth_does_not_log_secrets_or_command_errors(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "secret")
        with self.assertRaisesRegex(RuntimeError, "gcloud auth login") as err:
            inv.gcloud_user_token()
        self.assertNotIn("secret", str(err.exception))

    @patch("scripts.cloud_source_inventory.paged")
    def test_ecommerce_and_greenweez_found_without_data_rows(self, paged):
        def fake_paged(token, url, key):
            if key == "datasets":
                return [{"datasetReference": {"datasetId": "e_ticaret"}},
                        {"datasetReference": {"datasetId": "fvt_gsheet"}},
                        {"datasetReference": {"datasetId": "gz_raw_data"}}]
            if "e_ticaret/tables" in url:
                names = inv.EXPECTED["ecommerce"]
            elif "fvt_gsheet/tables" in url:
                names = inv.EXPECTED["greenweez_gsheet"]
            else:
                names = inv.EXPECTED["greenweez_raw"]
            return [{"tableReference": {"tableId": name}, "evil_data_row": "secret"}
                    for name in names]
        paged.side_effect = fake_paged
        result = inv.project_inventory("data-analiz-490513", "fake-in-memory-token")
        self.assertEqual(result["status"], "listed")
        self.assertEqual(len(result["datasets"]), 3)
        actual = {d["dataset"]: d for d in result["datasets"]}
        self.assertTrue(actual["e_ticaret"]["matches"]["ecommerce"]["all_required_tables_present"])
        self.assertTrue(actual["fvt_gsheet"]["matches"]["greenweez_gsheet"]["all_required_tables_present"])
        self.assertTrue(actual["gz_raw_data"]["matches"]["greenweez_raw"]["all_required_tables_present"])
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("fake-in-memory-token", json.dumps(result))
        self.assertEqual(len([x for x in paged.call_args_list if x.args[2] == "tables"]), 3)

    @patch("scripts.cloud_source_inventory.paged", side_effect=PermissionError("HTTP 403"))
    def test_denied_project_not_misreported_as_empty(self, paged):
        result = inv.project_inventory("workintech-working", "fake")
        self.assertEqual(result["status"], "access_denied_or_unavailable")
        self.assertEqual(len(result["metadata_errors"]), 1)

    @patch("scripts.cloud_source_inventory.paged")
    def test_denied_dataset_does_not_imply_no_source(self, paged):
        def fake_paged(token, url, key):
            if key == "datasets":
                return [{"datasetReference": {"datasetId": "fvt_gsheet"}}]
            raise PermissionError("HTTP 403")
        paged.side_effect = fake_paged
        result = inv.project_inventory("data-analiz-490513", "fake")
        self.assertEqual(result["datasets"][0]["status"], "table_list_unavailable")
        self.assertIsNone(result["datasets"][0]["table_count"])

    def test_refuse_unknown_projects(self):
        with self.assertRaises(ValueError):
            inv.project_inventory("other-project", "never-used-token")

    @patch("scripts.cloud_source_inventory.gcloud_user_token", return_value="ci-only")
    @patch("scripts.cloud_source_inventory.project_inventory")
    def test_report_contains_only_metadata_and_is_in_gitignored_target(self, project, token):
        project.side_effect = [
            {"project": p, "status": "listed", "datasets": [], "metadata_errors": []}
            for p in inv.PROJECTS
        ]
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "target" / "cloud_inventory" / "report.json"
            report = inv.run(output=output)
            self.assertTrue(output.exists())
            self.assertEqual(len(report["results"]), 2)
            saved = output.read_text()
            self.assertNotIn("ci-only", saved)
            self.assertNotIn("Authorization", saved)


if __name__ == "__main__":
    unittest.main()
