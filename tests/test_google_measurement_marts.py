"""Offline source-grain/metric-integrity tests; all records here are test fixtures."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from scripts import google_measurement_marts as gm


TS1 = "2026-10-15T12:00:00+00:00"
TS2 = "2026-10-16T12:00:00+00:00"


def ga4(*, ts=TS1, sessions=20, identity="123", date="2026-10-01"):
    return {
        "source": "ga4_data_api", "property_id": identity,
        "date_start": "2026-10-01", "date_end": "2026-10-14",
        "fetched_at_utc": ts, "partial": False,
        "rows": [{
            "date": date, "ga4_session_channel_group": "Organic Search",
            "sessions": sessions, "engaged_sessions": min(sessions, 12),
            "active_users": 11, "ecommerce_purchases": 2,
            "purchase_revenue_property_currency": 180.75,
        }]
    }


def gsc(*, ts=TS1):
    return {
        "source": "gsc_search_analytics_api", "site_property": "sc-domain:example.org",
        "date_start": "2026-10-01", "date_end": "2026-10-14",
        "fetched_at_utc": ts, "partial": False,
        "rows": [{
            "date": "2026-10-01", "device": "MOBILE",
            "clicks": 12, "impressions": 100,
            "ctr_ratio": .12, "average_position": 4.5,
        }]
    }


def pagespeed(*, ts=TS1):
    return {
        "source": "pagespeed_insights_api", "url": "https://example.org/",
        "strategy": "mobile", "fetched_at_utc": ts,
        "lighthouse_scores_0_to_100": {
            "performance": 92, "seo": 100, "best-practices": 98,
            "accessibility": 93,
        },
        "lab_metrics": {
            "largest-contentful-paint": 2250, "total-blocking-time": 95,
            "cumulative-layout-shift": 0.04,
        },
    }


class GoogleMartTests(unittest.TestCase):
    def test_ga4_grain_and_values(self):
        source, rows = gm.normalize_snapshot(ga4())
        self.assertEqual(source, "ga4_data_api")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sessions"], 20)
        self.assertEqual(rows[0]["property_id"], "123")
        self.assertNotIn("user_id", rows[0])

    def test_gsc_metrics_are_preserved_not_averaged(self):
        source, rows = gm.normalize_snapshot(gsc())
        self.assertEqual(rows[0]["ctr_ratio"], .12)
        self.assertEqual(rows[0]["average_position"], 4.5)
        self.assertEqual(source, "gsc_search_analytics_api")

    def test_pagespeed_lab_and_score_range(self):
        source, rows = gm.normalize_snapshot(pagespeed())
        self.assertEqual(source, "pagespeed_insights_api")
        self.assertEqual(rows[0]["lab_lcp_ms"], 2250)
        self.assertEqual(rows[0]["performance_score"], 92)
        bad = pagespeed()
        bad["lighthouse_scores_0_to_100"]["performance"] = 121
        with self.assertRaisesRegex(ValueError, "maximum"):
            gm.normalize_snapshot(bad)

    def test_reject_partial_unless_opted_in(self):
        partial = ga4()
        partial["partial"] = True
        with self.assertRaisesRegex(ValueError, "partial API extraction"):
            gm.normalize_snapshot(partial)
        self.assertEqual(gm.normalize_snapshot(partial, allow_partial=True)[0], "ga4_data_api")

    def test_reject_duplicate_grain_within_snapshot(self):
        bad = ga4()
        bad["rows"] = [bad["rows"][0], dict(bad["rows"][0])]
        with self.assertRaisesRegex(ValueError, "duplicate grain"):
            gm.normalize_snapshot(bad)

    def test_reject_out_of_range_rows_and_bad_metrics(self):
        bad = ga4(date="2026-09-30")
        with self.assertRaisesRegex(ValueError, "outside snapshot period"):
            gm.normalize_snapshot(bad)
        for field, value in [("sessions", -1), ("sessions", True), ("sessions", float("nan"))]:
            bad = ga4()
            bad["rows"][0][field] = value
            with self.assertRaises(ValueError):
                gm.normalize_snapshot(bad)
        bad = gsc()
        bad["rows"][0]["ctr_ratio"] = 1.2
        with self.assertRaises(ValueError):
            gm.normalize_snapshot(bad)

    def test_reject_inconsistent_engaged_sessions(self):
        bad = ga4(sessions=5)
        bad["rows"][0]["engaged_sessions"] = 6
        with self.assertRaisesRegex(ValueError, "exceeds"):
            gm.normalize_snapshot(bad)

    def test_reconcile_overlap_uses_newest_snapshot_not_sum(self):
        with tempfile.TemporaryDirectory() as root:
            input_path = Path(root)
            (input_path / "ga4_data_old.json").write_text(json.dumps(ga4()), encoding="utf-8")
            (input_path / "ga4_data_new.json").write_text(json.dumps(ga4(ts=TS2, sessions=25)), encoding="utf-8")
            tables, manifest = gm.read_and_reconcile(input_path)
            self.assertEqual(len(tables["ga4_data_api"]), 1)
            self.assertEqual(tables["ga4_data_api"][0]["sessions"], 25)
            self.assertEqual(manifest["replaced_overlapping_grains"], 1)

    def test_different_ga4_properties_never_coalesced(self):
        with tempfile.TemporaryDirectory() as root:
            src = Path(root)
            (src / "ga4_data_first.json").write_text(json.dumps(ga4(identity="123")), encoding="utf-8")
            (src / "ga4_data_second.json").write_text(json.dumps(ga4(identity="456")), encoding="utf-8")
            tables, manifest = gm.read_and_reconcile(src)
            self.assertEqual(len(tables["ga4_data_api"]), 2)
            self.assertEqual(manifest["source_summary"]["ga4_data_api"]["distinct_properties"], 2)

    def test_duplicate_snapshot_same_ts_disagreement_raises(self):
        with tempfile.TemporaryDirectory() as root:
            src = Path(root)
            (src / "ga4_data_a.json").write_text(json.dumps(ga4(sessions=10)), encoding="utf-8")
            (src / "ga4_data_b.json").write_text(json.dumps(ga4(sessions=25)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                gm.read_and_reconcile(src)

    def test_no_real_snapshots_does_not_generate_demo_metrics(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "No real"):
                gm.export_marts(Path(root), Path(root) / "output")

    def test_csv_export_has_three_independent_sources_and_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            src, output = Path(root) / "snapshots", Path(root) / "out"
            src.mkdir()
            for name, record in [
                ("ga4_data_one.json", ga4()), ("gsc_search_analytics_one.json", gsc()),
                ("pagespeed_insights_one.json", pagespeed()),
            ]:
                (src / name).write_text(json.dumps(record), encoding="utf-8")
            manifest = gm.export_marts(src, output)
            self.assertEqual(manifest["input_snapshot_count"], 3)
            for source, name in gm.OUTPUT_NAMES.items():
                with (output / name).open(encoding="utf-8") as stream:
                    records = list(csv.DictReader(stream))
                self.assertEqual(len(records), 1, source)
                self.assertEqual(records[0]["source_system"], source)
            self.assertTrue((output / "manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
