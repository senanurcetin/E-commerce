"""Offline first-touch regression: sqlite fixture + dbt SQL source contract.

Run: python -m unittest discover -s tests -p test_session_first_touch_order.py
SQLite checks deterministic ordering only; this does not execute BigQuery or DuckDB.
"""
import itertools
import sqlite3
import unittest
from pathlib import Path

MODEL = Path(__file__).resolve().parents[1] / "models" / "marts" / "fct_marketing_web_performance.sql"

# event_id, sequence_number, timestamp, traffic_source, browser
EVENTS = [
    (14, 2, "2026-10-01 08:00:00", "organic", "chrome"),
    (12, 2, "2026-10-01 08:00:00", "email", "firefox"),
    (8, 1, "2026-10-01 07:59:00", "unknown", "unknown"),
    (18, 3, "2026-10-01 08:02:00", "facebook", "safari"),
]


def first_known(rows, field):
    db = sqlite3.connect(":memory:")
    try:
        db.execute(
            "create table events (event_id integer, sequence_number integer, "
            "created_at text, traffic_source text, browser text)"
        )
        db.executemany("insert into events values (?, ?, ?, ?, ?)", rows)
        result = db.execute(
            f"select {field} from events where {field} <> 'unknown' "
            "order by sequence_number, created_at, event_id limit 1"
        ).fetchone()
        return result[0] if result else "unknown"
    finally:
        db.close()


class SessionFirstTouchTests(unittest.TestCase):
    def test_both_sql_adapters_have_unique_tiebreak_in_source_and_browser(self):
        sql = MODEL.read_text(encoding="utf-8")
        order = "order by sequence_number, event_created_at, event_id"
        self.assertEqual(sql.count(order), 4)
        self.assertIn(
            "array_agg(nullif(traffic_source, 'unknown') ignore nulls " + order, sql
        )
        self.assertIn(
            "array_agg(nullif(browser, 'unknown') ignore nulls " + order, sql
        )
        self.assertIn("first(traffic_source " + order, sql)
        self.assertIn("first(browser " + order, sql)

    def test_tied_events_choose_same_first_source_and_browser_in_any_input_order(self):
        for rows in itertools.permutations(EVENTS):
            self.assertEqual(first_known(rows, "traffic_source"), "email")
            self.assertEqual(first_known(rows, "browser"), "firefox")

    def test_all_unknown_session_has_no_false_attribution(self):
        rows = [(1, 1, "2026-10-01 08:00:00", "unknown", "unknown")]
        self.assertEqual(first_known(rows, "traffic_source"), "unknown")
        self.assertEqual(first_known(rows, "browser"), "unknown")


if __name__ == "__main__":
    unittest.main()
