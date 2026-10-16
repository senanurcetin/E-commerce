"""Pure Python tests for dashboard's non-mixing and denominator rules."""
from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from scripts import google_dashboard_data as gd


def ga4_row(**kwargs):
    return {
        "source_system": "ga4_data_api",
        "property_id": "123",
        "date": "2026-10-01",
        "ga4_session_channel_group": "Organic Search",
        "sessions": "100", "engaged_sessions": "60",
        "active_users": "80", "ecommerce_purchases": "4",
        "purchase_revenue_property_currency": "250.50",
        "extracted_at_utc": "2026-10-15T11:00:00+00:00",
        **kwargs,
    }


def gsc_row(**kwargs):
    base = {
        "source_system": "gsc_search_analytics_api", "site_property": "sc-domain:example.org",
        "date": "2026-10-01", "device": "MOBILE",
        "clicks": "2", "impressions": "10",
        "ctr_ratio": "0.2", "average_position": "2.0",
        "extracted_at_utc": "2026-10-15T11:00:00+00:00",
    }
    base.update(kwargs)
    return base


def psi_row(**kwargs):
    base = {
        "source_system": "pagespeed_insights_api", "url": "https://example.org/",
        "strategy": "mobile", "extracted_at_utc": "2026-10-15T11:00:00+00:00",
        "performance_score": "80", "accessibility_score": "90",
        "best_practices_score": "95", "seo_score": "91",
        "lab_fcp_ms": "800", "lab_lcp_ms": "2000", "lab_speed_index_ms": "1500",
        "lab_total_blocking_time_ms": "80", "lab_cls": "0.03",
    }
    base.update(kwargs)
    return base


class GoogleDashboardDataTests(unittest.TestCase):
    def test_ga4_uses_additive_kpis_but_not_distinct_active_users(self):
        rows = [ga4_row(), ga4_row(date="2026-10-02")]
        result = gd.kpis_ga4(rows)
        self.assertEqual(result["sessions"], 200)
        self.assertEqual(result["engagement_rate"], .60)
        self.assertEqual(result["ecommerce_purchases"], 8)
        self.assertEqual(result["purchase_revenue_in_property_currency"], 501)
        self.assertTrue(result["active_users_not_aggregated"])
        self.assertNotIn("active_users", result)

    def test_ga4_zero_sessions_is_unavailable_not_fake_rate(self):
        x = ga4_row(sessions="0", engaged_sessions="0")
        self.assertIsNone(gd.kpis_ga4([x])["engagement_rate"])

    def test_gsc_recomputes_ctr_and_position_by_impressions(self):
        result = gd.kpis_gsc([
            gsc_row(clicks="2", impressions="10", average_position="2.0"),
            gsc_row(device="DESKTOP", clicks="40", impressions="100", ctr_ratio="0.4", average_position="8.0"),
        ])
        self.assertAlmostEqual(result["ctr"], 42 / 110)
        self.assertAlmostEqual(result["impression_weighted_position"], 820 / 110)
        self.assertNotAlmostEqual(result["ctr"], (0.2 + 0.4) / 2)

    def test_gsc_zero_impressions_no_made_up_ctr(self):
        result = gd.kpis_gsc([gsc_row(clicks="0", impressions="0", ctr_ratio="0")])
        self.assertIsNone(result["ctr"])
        self.assertIsNone(result["impression_weighted_position"])

    def test_reject_negative_or_nonfinite_kpis(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            gd.kpis_ga4([ga4_row(sessions="-1")])
        with self.assertRaises(ValueError):
            gd.kpis_gsc([gsc_row(clicks="NaN")])

    def test_latest_pagespeed_is_scoped_by_url_and_device(self):
        items = [
            psi_row(),
            psi_row(performance_score="85", extracted_at_utc="2026-10-16T10:00:00+00:00"),
            psi_row(url="https://example.org/about", performance_score="91"),
            psi_row(strategy="desktop", performance_score="100"),
        ]
        latest = gd.latest_pagespeed(items)
        self.assertEqual(len(latest), 3)
        origin_mobile = next(r for r in latest if r["url"] == "https://example.org/" and r["strategy"] == "mobile")
        self.assertEqual(origin_mobile["performance_score"], "85")

    def test_date_filter_keeps_exact_requested_range(self):
        items = [ga4_row(date="2026-10-01"), ga4_row(date="2026-10-02")]
        rows = gd.filter_dates(items, date(2026, 10, 2), date(2026, 10, 2))
        self.assertEqual(len(rows), 1)

    def _write_valid_bundle(self, root: Path) -> None:
        input_rows = {
            "ga4": [ga4_row()],
            "gsc": [gsc_row()],
            "pagespeed": [psi_row()],
        }
        manifest = {
            "schema_version": 1,
            "data_status": "actual_api_snapshots_not_live_feed",
            "input_snapshot_count": 3,
            "partial_snapshot_count": 0,
            "source_summary": {},
        }
        for key, spec in gd.SCHEMA.items():
            data = input_rows[key]
            with (root / spec["filename"]).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=spec["required"])
                writer.writeheader()
                writer.writerows(data)
            manifest["source_summary"][spec["source_system"]] = {"rows": len(data)}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_bundle_requires_verified_manifest_and_exact_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(FileNotFoundError):
                gd.load_bundle(root)
            self._write_valid_bundle(root)
            tables, manifest = gd.load_bundle(root)
            self.assertEqual(len(tables["ga4"]), 1)
            self.assertEqual(manifest["partial_snapshot_count"], 0)
            with (root / "manifest.json").open("r+", encoding="utf-8") as stream:
                altered = json.load(stream)
            altered["data_status"] = "synthetic_seed"
            (root / "manifest.json").write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, "Unverified"):
                gd.load_bundle(root)

    def test_reject_missing_rows_partial_sources_and_identity_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_valid_bundle(root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["partial_snapshot_count"] = 1
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "Partial"):
                gd.load_bundle(root)
            manifest["partial_snapshot_count"] = 0
            manifest_path.write_text(json.dumps(manifest))
            path = root / gd.SCHEMA["gsc"]["filename"]
            csv_text = path.read_text()
            path.write_text(csv_text.replace("gsc_search_analytics_api", "other_system"))
            with self.assertRaisesRegex(ValueError, "source_system"):
                gd.load_bundle(root)


if __name__ == "__main__":
    unittest.main()
