"""Streamlit AppTest verifies empty-state honesty and test-only fixture rendering.

No account authentication, Google API requests, mock business claims or data writes.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from streamlit.testing.v1 import AppTest

from scripts.google_dashboard_data import SCHEMA


APP = Path(__file__).resolve().parents[1] / "dashboard/google_marketing_app.py"


def export_fixture(root: Path) -> None:
    """The following numbers are synthetic CI-only fixtures, never product metrics."""
    extracted = "2026-10-15T10:00:00+00:00"
    examples = {
        "ga4": {
            "source_system": "ga4_data_api", "property_id": "CI-ONLY-123",
            "date": "2026-10-01", "ga4_session_channel_group": "Organic Search",
            "sessions": "20", "engaged_sessions": "12", "active_users": "14",
            "ecommerce_purchases": "2", "purchase_revenue_property_currency": "45.50",
            "extracted_at_utc": extracted,
        },
        "gsc": {
            "source_system": "gsc_search_analytics_api", "site_property": "sc-domain:ci-only.example",
            "date": "2026-10-01", "device": "MOBILE",
            "clicks": "4", "impressions": "20", "ctr_ratio": "0.2",
            "average_position": "3.0", "extracted_at_utc": extracted,
        },
        "pagespeed": {
            "source_system": "pagespeed_insights_api", "url": "https://ci-only.example/",
            "strategy": "mobile", "extracted_at_utc": extracted,
            "performance_score": "0", "accessibility_score": "80", "best_practices_score": "90",
            "seo_score": "100", "lab_fcp_ms": "800", "lab_lcp_ms": "1700",
            "lab_speed_index_ms": "1500", "lab_total_blocking_time_ms": "70",
            "lab_cls": "0.05",
        },
    }
    manifest = {
        "schema_version": 1,
        "data_status": "actual_api_snapshots_not_live_feed",
        "partial_snapshot_count": 0,
        "input_snapshot_count": 3,
        "source_summary": {},
    }
    for source, spec in SCHEMA.items():
        record = examples[source]
        with (root / spec["filename"]).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=spec["required"])
            writer.writeheader()
            writer.writerow(record)
        manifest["source_summary"][spec["source_system"]] = {"rows": 1}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class GoogleMeasurementAppSmokeTests(unittest.TestCase):
    def test_no_snapshot_never_claims_real_metrics(self):
        with tempfile.TemporaryDirectory() as folder:
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            next(field for field in app.text_input if field.label == "Validated export folder").set_value(folder).run()
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            self.assertEqual(len(app.metric), 0, "Unavailable sources must not display KPI figures")
            self.assertEqual(len(app.tabs), 5, "Source tabs and separate lab tab stay visible without data")
            self.assertTrue(any("Website URL" == field.label for field in app.text_input))

    def test_commerce_lab_tab_never_fabricates_unconnected_revenue(self):
        with tempfile.TemporaryDirectory() as folder:
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            next(field for field in app.text_input if field.label == "Validated export folder").set_value(folder).run()
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            self.assertTrue(any("Commerce Lab" in tab.label for tab in app.tabs))
            self.assertFalse(any("Lab completed test checkouts" == metric.label for metric in app.metric))
            self.assertFalse(any("Purchase revenue · property currency" == metric.label for metric in app.metric))

    def test_ecommerce_demo_picker_prefills_url_without_scanning(self):
        with tempfile.TemporaryDirectory() as folder:
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            next(field for field in app.text_input if field.label == "Validated export folder").set_value(folder).run()
            store = next(field for field in app.selectbox if field.label == "Measurement target")
            store.set_value("Tricentis Demo Web Shop (third-party)").run()
            url = next(field for field in app.text_input if field.label == "Website URL")
            self.assertEqual(url.value, "https://demowebshop.tricentis.com/")
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            self.assertEqual(len(app.metric), 0, "Changing preset must not start an API call")

    def test_own_store_is_initial_website_target_and_no_api_is_called(self):
        with tempfile.TemporaryDirectory() as folder:
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            next(field for field in app.text_input if field.label == "Validated export folder").set_value(folder).run()
            store = next(field for field in app.selectbox if field.label == "Measurement target")
            self.assertEqual(store.value, "NEXUS Commerce Lab (owned test storefront)")
            url = next(field for field in app.text_input if field.label == "Website URL")
            self.assertEqual(url.value, "https://nexus-commerce-lab.vercel.app/")
            self.assertEqual(len(app.metric), 0)
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])

    def test_pagespeed_only_source_does_not_require_ga4_or_gsc(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            export_fixture(root)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for source in ("ga4", "gsc"):
                spec = SCHEMA[source]
                with (root / spec["filename"]).open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.DictWriter(stream, fieldnames=spec["required"])
                    writer.writeheader()
                manifest["source_summary"][spec["source_system"]]["rows"] = 0
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            next(field for field in app.text_input if field.label == "Validated export folder").set_value(folder).run()
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            labels = [metric.label for metric in app.metric]
            self.assertNotIn("Sessions", labels)
            self.assertIn("Performance", labels)

    def test_verified_csv_contract_drives_all_three_views(self):
        with tempfile.TemporaryDirectory() as folder:
            export_fixture(Path(folder))
            app = AppTest.from_file(str(APP), default_timeout=30).run()
            next(field for field in app.text_input if field.label == "Validated export folder").set_value(folder).run()
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            labels = [metric.label for metric in app.metric]
            self.assertIn("Sessions", labels)
            self.assertIn("Organic CTR", labels)
            self.assertIn("Performance", labels)


if __name__ == "__main__":
    unittest.main()
