"""Zero network: Greenweez local import audit validation, source registry and PBIP."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

import duckdb

from scripts.greenweez_import_audit import (
    load_import_audit, reporting_rows, validate_audit, FIELDS,
)
from scripts.nexus_workspace import inspect_sources
from scripts.build_powerbi import build


def example_audit():
    tables = {}
    for name, fields in FIELDS.items():
        tables[name] = {
            "rows": 2, "start_date": "2021-10-01", "end_date": "2021-10-02",
            "negative_count": {field: 0 for field in fields},
            "zero_count": {field: 1 if field == "turnover" else 0 for field in fields},
        }
    return {
        "schema_version": 1,
        "source_project": "workintech-working",
        "source_dataset": "fvt_gsheet",
        "provenance": "external_unverified",
        "financial_semantics_verified": False,
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "tables": tables,
        "join_coverage": {"orders_without_shipping": 1,
                          "orders_without_refund": 0},
    }


def save_db(root, audit):
    path = root / "integrations/greenweez/target/gsheet_real.duckdb"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA import_audit")
    con.execute("CREATE TABLE import_audit.source_quality(report JSON)")
    con.execute("INSERT INTO import_audit.source_quality VALUES (?)",
                [json.dumps(audit)])
    con.close()
    return path


class QualityEvidenceTests(unittest.TestCase):
    def test_valid_source_stays_unverified_and_has_no_id_fields(self):
        value = example_audit()
        self.assertIs(validate_audit(value), value)
        rows = reporting_rows(value)
        self.assertEqual(len(rows), 4)
        order = next(r for r in rows if r["table_name"] == "gwz_finance_orders_orders")
        self.assertEqual(order["unmatched_shipping_orders"], 1)
        self.assertEqual(order["zero_amount_values"], 1)
        self.assertEqual(order["finance_verified"], "NO")
        for row in rows:
            for forbidden in ("orders_id", "order_id", "revenue", "email", "customer"):
                self.assertNotIn(forbidden, row)

    def test_audit_rejects_tampering_and_false_certification(self):
        data = example_audit()
        for key, bad in (
            ("source_project", "data-analiz-490513"),
            ("provenance", "business_verified"),
            ("financial_semantics_verified", True),
        ):
            modified = json.loads(json.dumps(data))
            modified[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_audit(modified)
        modified = json.loads(json.dumps(data))
        modified["tables"]["gwz_finance_campaign"]["zero_count"]["cost"] = 4
        with self.assertRaises(ValueError):
            validate_audit(modified)
        modified = json.loads(json.dumps(data))
        modified["join_coverage"]["orders_without_refund"] = 999
        with self.assertRaises(ValueError):
            validate_audit(modified)

    def test_local_audit_visible_in_nexus_status_and_powerbi_without_data_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = save_db(root, example_audit())
            self.assertEqual(load_import_audit(local)["source_dataset"], "fvt_gsheet")
            status = {x["source"]: x for x in inspect_sources(root)}
            self.assertEqual(len(status), 9)
            self.assertEqual(status["greenweez_import_audit"]["status"], "external_unverified")
            self.assertFalse(status["greenweez_import_audit"]["real_business_verified"])
            self.assertEqual(status["greenweez"]["status"], "missing")
            result = build(root, root / "target/powerbi")
            self.assertEqual(result["exported_table_rows"]["GreenweezImportAudit"], 4)
            self.assertEqual(result["exported_table_rows"]["GreenweezFinance"], 0)
            with (root / "target/powerbi/marts/GreenweezImportAudit.csv").open(
                encoding="utf-8-sig", newline="",
            ) as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r["finance_verified"] == "NO" for r in rows))
            self.assertNotIn("orders_id", str(rows))
            self.assertNotIn("customer", str(rows))
            self.assertEqual(len(result["pages"]), 7)

    def test_invalid_local_audit_does_not_generate_any_powerbi_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = example_audit()
            invalid["provenance"] = "certified"
            save_db(root, invalid)
            states = {v["source"]:v for v in inspect_sources(root)}
            self.assertEqual(states["greenweez_import_audit"]["status"], "invalid")
            evidence = build(root, root / "target/powerbi")
            self.assertEqual(evidence["exported_table_rows"]["GreenweezImportAudit"], 0)

    def test_missing_local_audit_stays_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(load_import_audit(root / "missing.duckdb"))
            result = inspect_sources(root)
            self.assertEqual(len(result), 9)
            self.assertEqual({v["status"] for v in result}, {"missing"})
