"""Offline source-pinned E-Commerce BigQuery preflight regression tests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import ecommerce_bigquery_preflight as check
from scripts.cloud_source_inventory import EXPECTED, PROJECTS
from scripts.cloud_source_mapping import resolve


def metadata():
    result = []
    for project in PROJECTS:
        datasets = []
        if project == "workintech-working":
            datasets.append({
                "dataset": "e_ticaret", "status": "listed",
                "matches": {"ecommerce": {
                    "found": list(EXPECTED["ecommerce"]), "expected": 4,
                    "all_required_tables_present": True,
                }},
            })
        result.append({"project": project, "status": "listed",
                       "datasets": datasets, "metadata_errors": []})
    inventory = {"schema_version": 1, "results": result,
                 "scanned_at_utc": "2026-10-17T10:18:09+00:00"}
    return inventory, resolve(inventory)


class Client:
    def __init__(self, bad=None, too_expensive=False):
        self.queries, self.bad, self.too_expensive = [], bad, too_expensive
    def get_dataset(self, key):
        return type("Dataset", (), {"location": "EU"})()
    def get_table(self, key):
        fields = []
        for name in check.CONTRACT[key.rsplit(".", 1)[1]]:
            fields.append(type("Field", (), {
                "name": name, "field_type": "RECORD" if name == self.bad else "STRING",
                "mode": "NULLABLE",
            })())
        return type("Table", (), {"schema": fields})()
    def query(self, statement, *, location, job_config):
        self.queries.append((statement, location, job_config))
        n = 200_000_000 if self.too_expensive else 42
        return type("Job", (), {"total_bytes_processed": n})()


class BQ:
    @staticmethod
    def QueryJobConfig(**kw):
        return kw


class PreflightTests(unittest.TestCase):
    def test_inventory_exact_pin_not_alternative(self):
        inventory, mapping = metadata()
        check.verify_inventory(inventory, mapping)
        mapping["sources"]["ecommerce"]["complete_candidates"][0]["dataset"] = "other"
        with self.assertRaises(ValueError):
            check.verify_inventory(inventory, mapping)

    def test_four_dry_runs_with_no_row_reads(self):
        client = Client()
        report = check.preflight(client, BQ())
        self.assertEqual(len(client.queries), 4)
        self.assertEqual(set(report["tables"]), set(check.CONTRACT))
        self.assertFalse(report["rows_downloaded"])
        self.assertFalse(report["historical_marts_reconciled"])
        for query, region, config in client.queries:
            self.assertTrue(config["dry_run"])
            self.assertEqual(region, "EU")
            self.assertNotIn("SELECT *", query)
            self.assertIn("LIMIT 1", query)
        self.assertNotIn("session_123456", json.dumps(report))
        self.assertNotIn("Bearer ", json.dumps(report))

    def test_schema_type_and_query_cost_fail_closed(self):
        bad = Client(bad="id")
        with self.assertRaisesRegex(ValueError, "unsuitable"):
            check.preflight(bad, BQ())
        self.assertEqual(bad.queries, [])
        with self.assertRaisesRegex(ValueError, "exceeds cap"):
            check.preflight(Client(too_expensive=True), BQ())
        with self.assertRaises(ValueError):
            check.preflight(Client(), BQ(), cap=0)

    def test_cli_missing_inventory_does_not_auth_or_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "old.json"
            output.write_text("OLD")
            with patch.object(check, "token", side_effect=AssertionError("auth attempted")):
                rc = check.main(["--inventory", str(Path(tmp) / "missing.json"),
                                 "--output", str(output)])
            self.assertEqual(rc, 2)
            self.assertEqual(output.read_text(), "OLD")

    def test_atomic_receipt_rejects_untrusted_result(self):
        report = check.preflight(Client(), BQ())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_text("OLD")
            with self.assertRaises(ValueError):
                check.write_receipt(path, {"status": "fake", "rows_downloaded": True})
            self.assertEqual(path.read_text(), "OLD")
            check.write_receipt(path, report)
            self.assertEqual(json.loads(path.read_text())["region"], "EU")
