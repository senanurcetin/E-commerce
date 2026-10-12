#!/usr/bin/env python3
"""Offline source-contract checks for mutable order status in the dbt mart.

Run: python scripts/check_order_fact_refresh.py
This guards materialization/metric expressions; it is not a dbt compile or SQL run.
"""
import re
import unittest
from pathlib import Path

SQL_PATH = Path(__file__).resolve().parents[1] / "models" / "marts" / "fct_order_marketing.sql"


class OrderFactRefreshContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = SQL_PATH.read_text(encoding="utf-8")

    def test_fact_rebuilds_to_capture_existing_order_status_changes(self):
        self.assertRegex(self.sql, r"""materialized\s*=\s*['"]table['"]""")
        self.assertNotIn("is_incremental()", self.sql)
        self.assertNotRegex(self.sql, r"\{\{\s*this\s*\}\}")

    def test_current_status_controls_revenue_and_return_metrics(self):
        self.assertRegex(
            self.sql,
            r"lower\(order_item_status\)\s*=\s*'complete'\s+then\s+sale_price\s+else\s+0\s+end\s+as\s+revenue",
        )
        self.assertRegex(
            self.sql,
            r"lower\(order_item_status\)\s*=\s*'returned'\s+then\s+sale_price\s+else\s+0\s+end\s+as\s+returned_revenue",
        )
        self.assertRegex(
            self.sql,
            r"lower\(order_item_status\)\s*=\s*'returned'\s+then\s+1\s+else\s+0\s+end\s+as\s+is_returned_order",
        )

    def test_creation_timestamp_cannot_detect_a_later_return(self):
        previous_high_watermark = "2026-08-10 12:00:00"
        returned_item = {
            "created_at": "2026-01-02 09:00:00",
            "status": "returned",
            "sale_price": 125,
        }
        # Documents why the removed creation-time predicate was unsafe.
        self.assertFalse(returned_item["created_at"] > previous_high_watermark)
        self.assertEqual(
            returned_item["sale_price"] if returned_item["status"] == "returned" else 0, 125
        )


if __name__ == "__main__":
    unittest.main()
