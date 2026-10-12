#!/usr/bin/env python3
"""Run dbt financial invariant SQL against a synthetic SQLite table, offline.

This does not run dbt, BigQuery or DuckDB. It checks that the committed
singular SQL tests catch stale status metrics and invalid prices.
"""
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def run_assertion(name: str, records: list[tuple]) -> list[str]:
    sql = (TESTS / name).read_text(encoding="utf-8").replace(
        "{{ ref('fct_order_marketing') }}", "fct_order_marketing"
    )
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            "create table fct_order_marketing ("
            "order_item_sk text, order_item_status text, sale_price numeric, "
            "revenue numeric, returned_revenue numeric, "
            "is_completed_order integer, is_returned_order integer)"
        )
        connection.executemany(
            "insert into fct_order_marketing values (?, ?, ?, ?, ?, ?, ?)", records
        )
        return [row[0] for row in connection.execute(sql)]


class OrderFactInvariantSqlTests(unittest.TestCase):
    def test_current_complete_and_returned_orders_are_valid(self):
        records = [
            ("complete", "complete", 50, 50, 0, 1, 0),
            ("returned", "returned", 20, 0, 20, 0, 1),
            ("processing", "processing", 10, 0, 0, 0, 0),
        ]
        self.assertEqual(run_assertion("fct_order_marketing_status_reconciliation.sql", records), [])
        self.assertEqual(run_assertion("fct_order_marketing_invalid_sale_price.sql", records), [])

    def test_stale_revenue_and_return_flag_are_detected(self):
        records = [
            ("stale", "returned", 50, 50, 0, 1, 0),
            ("bad-null-metric", "complete", 10, None, 0, 1, 0),
        ]
        self.assertEqual(
            set(run_assertion("fct_order_marketing_status_reconciliation.sql", records)),
            {"stale", "bad-null-metric"},
        )

    def test_invalid_prices_are_detected_even_for_noncompleted_orders(self):
        records = [
            ("missing", "processing", None, 0, 0, 0, 0),
            ("negative", "returned", -10, 0, -10, 0, 1),
            ("valid", "complete", 10, 10, 0, 1, 0),
        ]
        self.assertEqual(
            set(run_assertion("fct_order_marketing_invalid_sale_price.sql", records)),
            {"missing", "negative"},
        )


if __name__ == "__main__":
    unittest.main()
