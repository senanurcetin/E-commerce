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



class ScopedSheetsEvidenceTests(unittest.TestCase):
    """Partial scan permits preview only for exact source already configured in dbt."""

    @staticmethod
    def incomplete():
        m = mapping()
        m["inventory_complete"] = False
        m["inventory_scanned_at_utc"] = "2026-10-17T10:18:09+00:00"
        item = m["sources"]["greenweez_gsheet"]
        item["status"] = "inventory_incomplete"
        item["complete_candidates"] = [
            {"project": "workintech-working", "dataset": "fvt_gsheet"}
        ]
        item.pop("suggested_dbt_vars", None)
        inventory = {
            "schema_version": 1, "scanned_at_utc": m["inventory_scanned_at_utc"],
            "results": [
                {"project": "workintech-working", "status": "listed",
                 "datasets": [
                    {"dataset": "_unreadable", "status": "table_list_unavailable"},
                    {"dataset": "fvt_gsheet", "status": "listed",
                     "matches": {"greenweez_gsheet": {
                         "found": list(loader.TABLES),
                         "expected": len(loader.TABLES),
                         "all_required_tables_present": True,
                     }}}
                 ], "metadata_errors": [{"dataset": "_unreadable", "reason": "HTTP 403"}]},
                {"project": "data-analiz-490513", "status": "listed",
                 "datasets": [], "metadata_errors": []},
            ]
        }
        return m, inventory

    def test_unrelated_403_does_not_block_exact_pinned_source(self):
        report, inventory = self.incomplete()
        self.assertEqual(loader.checked_source(report, inventory),
                         ("workintech-working", "fvt_gsheet"))
        with self.assertRaisesRegex(ValueError, "requires"):
            loader.checked_source(report)

    def test_modified_table_membership_denied(self):
        report, inventory = self.incomplete()
        inventory["results"][0]["datasets"][1]["matches"]["greenweez_gsheet"]["found"].pop()
        with self.assertRaisesRegex(ValueError, "expected"):
            loader.checked_source(report, inventory)

    def test_mismatched_scan_time_denied(self):
        report, inventory = self.incomplete()
        inventory["scanned_at_utc"] = "older scan"
        with self.assertRaisesRegex(ValueError, "different scans"):
            loader.checked_source(report, inventory)

    def test_another_project_cannot_be_inferred_from_partial_scan(self):
        report, inventory = self.incomplete()
        report["sources"]["greenweez_gsheet"]["complete_candidates"][0]["project"] = "data-analiz-490513"
        with self.assertRaisesRegex(ValueError, "explicitly pinned"):
            loader.checked_source(report, inventory)

    def test_unlisted_pinned_dataset_denied(self):
        report, inventory = self.incomplete()
        inventory["results"][0]["datasets"].pop()
        with self.assertRaisesRegex(ValueError, "not listed once"):
            loader.checked_source(report, inventory)


class PrepublicationRowContractsTests(unittest.TestCase):
    @staticmethod
    def orders():
        import pandas as pd
        return pd.DataFrame({"orders_id":[10,11],
            "datetime":["2021-10-01 10:00:00UTC","2021-10-02 11:00:00UTC"],
            "turnover":[0,50],"purchase_cost":[0,55],"ship_fee":[5,5]})

    def test_bigquery_projection_excludes_extraneous_columns(self):
        statement = loader.table_sql("workintech-working","fvt_gsheet",
                                     "gwz_finance_orders_orders",20)
        self.assertNotIn("SELECT *",statement)
        self.assertNotIn("_fivetran_synced",statement)
        for field in loader.TABLES["gwz_finance_orders_orders"]:
            self.assertIn(chr(96)+field+chr(96),statement)

    def test_zero_revenue_is_not_silently_removed(self):
        summary=loader.validate_import_frame("gwz_finance_orders_orders",self.orders())
        self.assertEqual(summary["rows"],2)
        self.assertEqual(summary["zero_count"]["turnover"],1)
        self.assertNotIn("orders_id",json.dumps(summary))

    def test_duplicate_or_invalid_ids_fail(self):
        data=self.orders()
        data.loc[1,"orders_id"]=10
        with self.assertRaisesRegex(ValueError,"duplicates 1"):
            loader.validate_import_frame("gwz_finance_orders_orders",data)
        data=self.orders()
        data.loc[1,"orders_id"]="invalid"
        with self.assertRaisesRegex(ValueError,"invalid order identifiers 1"):
            loader.validate_import_frame("gwz_finance_orders_orders",data)

    def test_invalid_dates_or_amounts_fail(self):
        data=self.orders()
        data.loc[0,"datetime"]="bad-date"
        with self.assertRaisesRegex(ValueError,"calendar dates"):
            loader.validate_import_frame("gwz_finance_orders_orders",data)
        data=self.orders()
        data.loc[0,"turnover"]=float("inf")
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            loader.validate_import_frame("gwz_finance_orders_orders",data)

    def test_campaign_duplicate_date_and_pii_extra_field_rejected(self):
        import pandas as pd
        frame=pd.DataFrame({"datetime":["2021-10-01","2021-10-01"],"cost":[1,2]})
        with self.assertRaisesRegex(ValueError,"duplicate campaign day"):
            loader.validate_import_frame("gwz_finance_campaign",frame)
        data=self.orders()
        data["customer_email"]="private@example.org"
        with self.assertRaisesRegex(ValueError,"invalid projection"):
            loader.validate_import_frame("gwz_finance_orders_orders",data)
