"""Offline E-Commerce historical mart adapter unit tests; CI-only synthetic fixtures."""
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import tempfile
import unittest

import duckdb
from scripts import ecommerce_marts_bridge as bridge


def fixture():
    return {
        "schema_version": 1,
        "source_system": bridge.SOURCE,
        "provenance": "synthetic_ci",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": "b" * 64,
        "tables": {
            "orders": [
                {"date": "2023-01-02", "completed_orders": 1,
                 "returned_orders": 0, "completed_revenue": 150.0, "returned_line_revenue": 0.0},
                {"date": "2023-01-03", "completed_orders": 1,
                 "returned_orders": 1, "completed_revenue": 20.0, "returned_line_revenue": 35.0},
            ],
            "sessions": [
                {"date": "2023-01-02", "sessions": 2, "converted_sessions": 1, "page_view_events": 5},
                {"date": "2023-01-03", "sessions": 1, "converted_sessions": 1, "page_view_events": 3},
            ],
        },
        "row_counts": {"orders": 2, "sessions": 2},
    }


def create_db(path: Path):
    con = duckdb.connect(str(path))
    try:
        con.execute("create schema analytics")
        con.execute("""create table analytics.fct_order_marketing (
            order_date date, order_item_status varchar,
            order_id integer, revenue double, returned_revenue double)""")
        con.executemany("insert into analytics.fct_order_marketing values (?,?,?,?,?)", [
            ("2023-01-02", "Complete", 101, 100.0, 0.0),
            ("2023-01-02", "Complete", 101, 50.0, 0.0),
            ("2023-01-03", "Returned", 102, 0.0, 35.0),
            ("2023-01-03", "Complete", 103, 20.0, 0.0),
        ])
        con.execute("""create table analytics.fct_marketing_web_performance(
            session_date date, is_converted int, page_view_events int)""")
        con.executemany("insert into analytics.fct_marketing_web_performance values (?,?,?)", [
            ("2023-01-02", 1, 3),
            ("2023-01-02", 0, 2),
            ("2023-01-03", 1, 3),
        ])
    finally:
        con.close()


class EcommerceMartsTests(unittest.TestCase):
    def test_source_only_aggregates_and_distinct_orders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "db.duckdb"
            out = root / "export.json"
            create_db(db)
            result = bridge.export_from_duckdb(db, out)
            self.assertEqual(result["tables"]["orders"][0]["completed_orders"], 1)
            self.assertEqual(result["tables"]["orders"][0]["completed_revenue"], 150.0)
            self.assertEqual(result["tables"]["sessions"][0]["sessions"], 2)
            self.assertEqual(result["provenance"], "synthetic_ci")
            self.assertEqual(bridge.load_snapshot(out), result)
            for forbidden in ("order_id", "user_id", "email", "address", "customer"):
                self.assertNotIn('"' + forbidden + '"', out.read_text().lower())

    def test_missing_source_never_returns_fake_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.json"
            self.assertIsNone(bridge.load_snapshot(missing))
            with self.assertRaises(FileNotFoundError):
                bridge.export_from_duckdb(Path(folder) / "unknown.duckdb")

    def test_source_provenance_cannot_self_certify_actual(self):
        with self.assertRaises(ValueError):
            bridge.validate_snapshot({**fixture(), "provenance": "verified_real"})
        with self.assertRaises(ValueError):
            bridge.validate_snapshot({**fixture(), "source_system": "greenweez_dbt_marts"})
        good = bridge.validate_snapshot({**fixture(), "provenance": "external_unverified"})
        self.assertEqual(good["provenance"], "external_unverified")

    def test_bad_grains_and_row_identity_refused(self):
        for mutate in ("duplicate", "nan", "raw-id", "count"):
            snap = fixture()
            if mutate == "duplicate":
                snap["tables"]["orders"][1]["date"] = "2023-01-02"
            if mutate == "nan":
                snap["tables"]["orders"][0]["completed_revenue"] = float("nan")
            if mutate == "raw-id":
                snap["tables"]["sessions"][0]["user_id"] = 123
            if mutate == "count":
                snap["row_counts"]["orders"] = 999
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                bridge.validate_snapshot(snap)

    def test_converted_sessions_cannot_exceed_sessions(self):
        data = fixture()
        data["tables"]["sessions"][0]["converted_sessions"] = 99
        with self.assertRaisesRegex(ValueError, "Converted sessions"):
            bridge.validate_snapshot(data)


if __name__ == "__main__":
    unittest.main()
