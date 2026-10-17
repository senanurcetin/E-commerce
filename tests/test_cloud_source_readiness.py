"""Unit tests for metadata-only P0 readiness: no cloud credentials or row queries."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from scripts import cloud_source_readiness as ready
from scripts.cloud_source_inventory import EXPECTED, PROJECTS
from scripts.cloud_source_mapping import resolve


def fixture():
    entries = {
        "workintech-working": [
            ("e_ticaret", "ecommerce", EXPECTED["ecommerce"]),
            ("fvt_gsheet", "greenweez_gsheet", EXPECTED["greenweez_gsheet"]),
        ],
        "data-analiz-490513": [
            ("thelook_ecommerce", "ecommerce", EXPECTED["ecommerce"]),
            ("gz_raw_data", "greenweez_raw", EXPECTED["greenweez_raw"][:3]),
        ],
    }
    results = []
    for project in PROJECTS:
        datasets = []
        for dataset, domain, present in entries[project]:
            datasets.append({
                "dataset": dataset, "status": "listed", "table_count": len(present),
                "matches": {domain: {
                    "found": list(present), "coverage": len(present),
                    "expected": len(EXPECTED[domain]),
                    "all_required_tables_present": len(present) == len(EXPECTED[domain]),
                }},
            })
        if project == "workintech-working":
            datasets.append({"dataset": "_unreadable", "status": "table_list_unavailable",
                             "matches": {}, "table_count": None})
        results.append({
            "project": project, "status": "listed", "datasets": datasets,
            "metadata_errors": ([{"reason": "HTTP 403", "dataset": "_unreadable"}]
                                if project == "workintech-working" else []),
        })
    report = {"schema_version": 1, "scanned_at_utc": "2026-10-17T10:18:09+00:00",
              "results": results}
    return report, resolve(report)


class SourceReadinessTests(unittest.TestCase):
    def test_two_pinned_sources_ready_but_live_preflight_never_passed(self):
        inventory, mapping = fixture()
        report = ready.evaluate(inventory, mapping)
        self.assertFalse(report["global_inventory_complete"])
        self.assertFalse(report["data_rows_queried"])
        self.assertFalse(report["p0_live_preflight_complete"])
        self.assertEqual(report["sources"]["greenweez_gsheet"]["tables_found"], 4)
        self.assertEqual(report["sources"]["ecommerce"]["tables_found"], 4)
        self.assertEqual(report["sources"]["ecommerce_alternative"]["status"],
                         "separate_candidate_do_not_union")
        self.assertEqual(report["sources"]["greenweez_raw"]["tables_found"], 3)
        self.assertEqual(report["sources"]["greenweez_raw"]["tables_required"], 7)
        self.assertNotIn("_unreadable", json.dumps(report))
        self.assertNotIn("HTTP 403", json.dumps(report))

    def test_reject_inconsistent_or_rewritten_mapping(self):
        inventory, mapping = fixture()
        mapping["sources"]["greenweez_gsheet"]["complete_candidates"][0]["dataset"] = "fake"
        with self.assertRaisesRegex(ValueError, "differs"):
            ready.evaluate(inventory, mapping)
        inventory, mapping = fixture()
        mapping["inventory_scanned_at_utc"] = "old scan"
        with self.assertRaisesRegex(ValueError, "do not match"):
            ready.evaluate(inventory, mapping)

    def test_missing_pinned_tables_block_without_fallback(self):
        inventory, _ = fixture()
        inventory["results"][0]["datasets"][1]["matches"]["greenweez_gsheet"]["found"].pop()
        mapping = resolve(inventory)
        report = ready.evaluate(inventory, mapping)
        self.assertEqual(report["sources"]["greenweez_gsheet"]["status"], "blocked")
        self.assertFalse(report["sources"]["greenweez_gsheet"]["table_names_confirmed"])

    def test_offline_cli_outputs_only_restricted_metadata(self):
        inventory, mapping = fixture()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "original.json"
            mapping_file = folder / "mapping.json"
            output = folder / "p0.json"
            source.write_text(json.dumps(inventory))
            mapping_file.write_text(json.dumps(mapping))
            rc = ready.main(["--inventory", str(source), "--mapping", str(mapping_file),
                             "--output", str(output)])
            self.assertEqual(rc, 0)
            result = json.loads(output.read_text())
            self.assertEqual(result["sources"]["greenweez_raw"]["status"],
                             "blocked_incomplete_marketing_source_tables")
            self.assertNotIn("_unreadable", output.read_text())
            self.assertFalse(result["financial_semantics_verified"])


class LiveReceiptConsumptionTests(unittest.TestCase):
    @staticmethod
    def receipt():
        fields = ready.GSHEET_FIELDS
        return {
            "schema_version": 1,
            "source": {"project": "workintech-working", "dataset": "fvt_gsheet"},
            "billing_project": "workintech-working",
            "region": "EU",
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "live_schema_and_cost_dry_run_passed",
            "per_query_maximum_bytes_billed": 50_000_000,
            "max_rows_per_table_on_later_import": 250_000,
            "tables": {table: {
                "estimated_bytes_scanned": 250,
                "schema_columns": len(cols),
                "required_field_types": {col: "STRING" for col in cols},
            } for table, cols in fields.items()},
            "rows_downloaded_by_preflight": False,
            "finance_data_reconciled": False,
            "powerbi_desktop_accepted": False,
            "warning": "Not certified finance data",
        }

    def test_fresh_receipt_remains_operator_unverified_and_no_row_claim(self):
        inventory, mapping = fixture()
        result = ready.evaluate(inventory, mapping, self.receipt())
        evidence = result["greenweez_live_preflight_receipt"]
        self.assertEqual(evidence["receipt_table_count"], 4)
        self.assertEqual(evidence["estimated_bytes_total"], 1_000)
        self.assertEqual(evidence["status"],
                         "recent_local_receipt_requires_operator_verification")
        self.assertTrue(evidence["operator_verification_required"])
        self.assertFalse(result["data_rows_queried"])
        self.assertFalse(result["p0_live_preflight_complete"])
        self.assertFalse(result["financial_semantics_verified"])

    def test_stale_receipt_is_not_passed(self):
        r = self.receipt()
        r["observed_at_utc"] = (datetime.now(timezone.utc) -
                               timedelta(days=2)).isoformat()
        self.assertEqual(ready.read_live_receipt(r)["status"],
                         "stale_local_receipt")

    def test_foreign_source_and_false_finance_claim_rejected(self):
        for mutate in ("source", "verified", "row_read", "unknown_field", "overbudget"):
            with self.subTest(mutate=mutate):
                r = self.receipt()
                if mutate == "source":
                    r["source"]["project"] = "data-analiz-490513"
                elif mutate == "verified":
                    r["finance_data_reconciled"] = True
                elif mutate == "row_read":
                    r["rows_downloaded_by_preflight"] = True
                elif mutate == "unknown_field":
                    r["tables"]["gwz_finance_campaign"]["required_field_types"]["customer_email"] = "STRING"
                else:
                    r["tables"]["gwz_finance_campaign"]["estimated_bytes_scanned"] = 60_000_000
                with self.assertRaises(ValueError):
                    ready.read_live_receipt(r)

    def test_full_cli_detects_local_receipt_without_api_access(self):
        inventory, mapping = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            i, m, l, o = [folder / name for name in
                          ("inventory.json", "mapping.json", "live.json", "out.json")]
            i.write_text(json.dumps(inventory))
            m.write_text(json.dumps(mapping))
            l.write_text(json.dumps(self.receipt()))
            self.assertEqual(ready.main(["--inventory", str(i),
                                         "--mapping", str(m),
                                         "--live-preflight", str(l),
                                         "--output", str(o)]), 0)
            report = json.loads(o.read_text())
            self.assertFalse(report["p0_live_preflight_complete"])
            self.assertEqual(
                report["greenweez_live_preflight_receipt"]["receipt_table_count"], 4)
