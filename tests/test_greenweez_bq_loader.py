"""Safety tests for Greenweez metadata-gated BigQuery -> DuckDB loader (offline)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "integrations/greenweez/scripts/load_gsheet_from_bigquery.py"
spec = importlib.util.spec_from_file_location("greenweez_bq_loader", PATH)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


def mapping():
    return {
        "schema_version": 1, "inventory_complete": True,
        "sources": {"greenweez_gsheet": {
            "status": "ready_for_manual_review",
            "required_tables": list(loader.TABLES),
            "complete_candidates": [{"project": "data-analiz-490513", "dataset": "fvt_gsheet"}],
            "suggested_dbt_vars": {
                "greenweez_gsheet_project": "data-analiz-490513",
                "greenweez_gsheet_dataset": "fvt_gsheet",
            }
        }}
    }


class SourceGuardTests(unittest.TestCase):
    def test_unique_inventory_only(self):
        self.assertEqual(loader.checked_source(mapping()),
                         ("data-analiz-490513", "fvt_gsheet"))

    def test_partial_metadata_or_ambiguous_rejected(self):
        p = mapping()
        p["inventory_complete"] = False
        with self.assertRaisesRegex(ValueError, "incomplete"):
            loader.checked_source(p)
        p["inventory_complete"] = True
        p["sources"]["greenweez_gsheet"]["complete_candidates"].append(
            {"project": "workintech-working", "dataset": "fvt_gsheet"})
        with self.assertRaisesRegex(ValueError, "one"):
            loader.checked_source(p)

    def test_incorrect_contract_and_mismatched_dbt_vars_rejected(self):
        p = mapping()
        p["sources"]["greenweez_gsheet"]["required_tables"].remove("gwz_finance_campaign")
        with self.assertRaisesRegex(ValueError, "contract"):
            loader.checked_source(p)
        p = mapping()
        p["sources"]["greenweez_gsheet"]["suggested_dbt_vars"]["greenweez_gsheet_dataset"] = "wrong"
        with self.assertRaisesRegex(ValueError, "agree"):
            loader.checked_source(p)

    def test_reject_sql_identifier_injection(self):
        p = mapping()
        p["sources"]["greenweez_gsheet"]["complete_candidates"][0]["dataset"] = "fvt_gsheet` UNION SELECT"
        with self.assertRaises(ValueError):
            loader.checked_source(p)
        with self.assertRaises(ValueError):
            loader.table_sql("data-analiz-490513", "fvt_gsheet;drop", "gwz_finance_campaign", 5)
        with self.assertRaises(ValueError):
            loader.table_sql("data-analiz-490513", "fvt_gsheet", "evil_table", 5)

    def test_guard_bounded_sql(self):
        sql = loader.table_sql("data-analiz-490513", "fvt_gsheet",
                               "gwz_finance_campaign", 10)
        self.assertIn("LIMIT 11", sql)
        self.assertIn("`data-analiz-490513.fvt_gsheet.gwz_finance_campaign`", sql)

    def test_no_mapping_never_auths_and_never_touches_existing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping_path = Path(tmp) / "mapping.json"
            db_path = Path(tmp) / "gsheet_real.duckdb"
            db_path.write_bytes(b"KEEP_OLD_DB")
            with patch.object(loader, "access_token", side_effect=AssertionError("auth forbidden")):
                result = loader.main(["--mapping", str(mapping_path), "--output", str(db_path), "--execute"])
            self.assertEqual(result, 2)
            self.assertEqual(db_path.read_bytes(), b"KEEP_OLD_DB")

    def test_unverified_mapping_does_not_auth(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping_path = Path(tmp) / "mapping.json"
            p = mapping()
            p["sources"]["greenweez_gsheet"]["status"] = "ambiguous"
            mapping_path.write_text(json.dumps(p), encoding="utf-8")
            with patch.object(loader, "access_token", side_effect=AssertionError("auth forbidden")):
                result = loader.main(["--mapping", str(mapping_path), "--execute"])
            self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
